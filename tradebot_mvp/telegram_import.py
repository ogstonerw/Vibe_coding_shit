from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
import stat
import sys
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self

from .config import ConfigError, MvpConfig, load_config
from .contracts import Outcome, Source
from .journal import ConfigFingerprintMismatch, Journal
from .parser import EnvelopeError, parse_envelope
from .replay import render_summary
from .service import OfflineSignalService

MAX_EXPORT_BYTES = 64 * 1024 * 1024
MAX_EXPORT_MESSAGES = 100_000
MAX_TIMESTAMP = 253_402_300_799
MAX_IDENTITY_INTEGER = 2**63 - 1
MAX_JSON_INTEGER_DIGITS = 32
SUPPORTED_CHANNEL_TYPES = frozenset({"private_channel", "public_channel"})
SKIPPED_MESSAGE_TYPES = frozenset({"service", "unsupported"})

HISTORICAL_IMPORT_SCHEMA = """
CREATE TABLE IF NOT EXISTS telegram_import_events (
    source TEXT NOT NULL,
    channel_key TEXT NOT NULL,
    message_id TEXT NOT NULL,
    revision TEXT NOT NULL,
    message_timestamp TEXT NOT NULL,
    edited_timestamp TEXT,
    event_timestamp TEXT NOT NULL,
    event_epoch INTEGER NOT NULL CHECK (
        event_epoch >= 0 AND event_epoch <= 253402300799
    ),
    reply_to_message_id TEXT,
    reply_to_peer_key TEXT,
    import_payload_hash TEXT NOT NULL,
    export_format TEXT NOT NULL CHECK (export_format = 'TELEGRAM_DESKTOP_JSON'),
    PRIMARY KEY (source, channel_key, message_id, revision),
    FOREIGN KEY (source, channel_key, message_id, revision)
        REFERENCES events (source, channel_key, message_id, revision)
) STRICT;

CREATE TABLE IF NOT EXISTS telegram_import_skipped (
    source TEXT NOT NULL,
    channel_key TEXT NOT NULL,
    message_id TEXT NOT NULL,
    revision TEXT NOT NULL,
    message_timestamp TEXT,
    edited_timestamp TEXT,
    event_timestamp TEXT,
    event_epoch INTEGER CHECK (
        event_epoch IS NULL
        OR (event_epoch >= 0 AND event_epoch <= 253402300799)
    ),
    reply_to_message_id TEXT,
    reply_to_peer_key TEXT,
    skip_reason TEXT NOT NULL,
    import_payload_hash TEXT NOT NULL,
    export_format TEXT NOT NULL CHECK (export_format = 'TELEGRAM_DESKTOP_JSON'),
    PRIMARY KEY (source, channel_key, message_id, revision)
) STRICT;

CREATE TABLE IF NOT EXISTS telegram_import_state (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    event_epoch INTEGER NOT NULL CHECK (
        event_epoch >= 0 AND event_epoch <= 253402300799
    ),
    source TEXT NOT NULL,
    channel_key TEXT NOT NULL,
    message_id TEXT NOT NULL,
    revision TEXT NOT NULL,
    import_payload_hash TEXT NOT NULL
) STRICT;
"""


class DuplicateJsonKey(ValueError):
    pass


class InvalidJsonNumber(ValueError):
    pass


class TelegramImportError(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class HistoricalMessage:
    source: Source
    channel_id: str
    message_id: int
    revision: int
    message_timestamp: str
    edited_timestamp: str | None
    event_timestamp: str
    event_epoch: int
    reply_to_message_id: int | None
    reply_to_peer_id: str | None
    text: str
    import_payload_hash: str

    @property
    def channel_key(self) -> str:
        return hashlib.sha256(self.channel_id.encode()).hexdigest()

    @property
    def db_identity(self) -> tuple[str, str, str, str]:
        return (
            self.source.value,
            self.channel_key,
            str(self.message_id),
            str(self.revision),
        )

    @property
    def reply_to_peer_key(self) -> str | None:
        if self.reply_to_peer_id is None:
            return None
        return hashlib.sha256(self.reply_to_peer_id.encode()).hexdigest()

    @property
    def envelope(self) -> dict[str, str | int]:
        return {
            "channel_id": self.channel_id,
            "message_id": self.message_id,
            "revision": self.revision,
            "source": self.source.value,
            "text": self.text,
            "timestamp": self.event_timestamp,
        }

    @property
    def sort_key(self) -> tuple[int, str, str, int, int, str]:
        return (
            self.event_epoch,
            self.source.value,
            self.channel_key,
            self.message_id,
            self.revision,
            self.import_payload_hash,
        )


@dataclass(frozen=True, slots=True)
class HistoricalSkippedMessage:
    source: Source
    channel_id: str
    message_id: int
    revision: int | None
    message_timestamp: str | None
    edited_timestamp: str | None
    event_timestamp: str | None
    event_epoch: int | None
    reply_to_message_id: int | None
    reply_to_peer_id: str | None
    skip_reason: str
    import_payload_hash: str

    @property
    def channel_key(self) -> str:
        return hashlib.sha256(self.channel_id.encode()).hexdigest()

    @property
    def revision_key(self) -> str:
        return "UNAVAILABLE" if self.revision is None else str(self.revision)

    @property
    def db_identity(self) -> tuple[str, str, str, str]:
        return (
            self.source.value,
            self.channel_key,
            str(self.message_id),
            self.revision_key,
        )

    @property
    def reply_to_peer_key(self) -> str | None:
        if self.reply_to_peer_id is None:
            return None
        return hashlib.sha256(self.reply_to_peer_id.encode()).hexdigest()

    @property
    def sort_key(self) -> tuple[int, str, str, int, int, str] | None:
        if self.event_epoch is None or self.revision is None:
            return None
        return (
            self.event_epoch,
            self.source.value,
            self.channel_key,
            self.message_id,
            self.revision,
            self.import_payload_hash,
        )

    @property
    def stable_key(self) -> tuple[str, str, int, str, str]:
        return (
            self.source.value,
            self.channel_key,
            self.message_id,
            self.revision_key,
            self.import_payload_hash,
        )


HistoricalRecord = HistoricalMessage | HistoricalSkippedMessage
EventSortKey = tuple[int, str, str, int, int, str]


@dataclass(frozen=True, slots=True)
class ImportBatch:
    records: tuple[HistoricalMessage, ...]
    skipped_records: tuple[HistoricalSkippedMessage, ...]
    input_shape: str
    source: Source
    chat_id: str
    input_messages: int
    exact_export_duplicates: int

    @property
    def chat_key(self) -> str:
        return hashlib.sha256(self.chat_id.encode()).hexdigest()

    @property
    def skipped_messages(self) -> int:
        return len(self.skipped_records)


def _closed_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKey(key)
        result[key] = value
    return result


def _bounded_json_integer(value: str) -> int:
    digits = value.removeprefix("-")
    if len(digits) > MAX_JSON_INTEGER_DIGITS:
        raise InvalidJsonNumber(value)
    return int(value)


def _bounded_json_float(value: str) -> float:
    if len(value) > 128:
        raise InvalidJsonNumber(value)
    parsed = float(value)
    if not math.isfinite(parsed):
        raise InvalidJsonNumber(value)
    return parsed


def _reject_json_constant(value: str) -> None:
    raise InvalidJsonNumber(value)


def _canonical_hash(payload: object, *, reason: str) -> str:
    try:
        canonical = json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode()).hexdigest()
    except (RecursionError, TypeError, UnicodeEncodeError, ValueError) as exc:
        raise TelegramImportError(reason) from exc


def _parse_identifier(value: object, *, reason: str) -> int:
    if type(value) is not int:
        raise TelegramImportError(reason)
    parsed = value
    if parsed < 1 or parsed > MAX_IDENTITY_INTEGER:
        raise TelegramImportError(reason)
    return parsed


def _parse_epoch(value: object, *, reason: str) -> tuple[int, str]:
    if (
        type(value) is not str
        or not value
        or len(value) > len(str(MAX_TIMESTAMP))
        or not value.isascii()
        or not value.isdecimal()
        or (len(value) > 1 and value.startswith("0"))
    ):
        raise TelegramImportError(reason)
    parsed = int(value)
    if parsed < 0 or parsed > MAX_TIMESTAMP:
        raise TelegramImportError(reason)
    try:
        timestamp = datetime.fromtimestamp(parsed, tz=UTC).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    except (OverflowError, OSError, ValueError) as exc:
        raise TelegramImportError(reason) from exc
    return parsed, timestamp


def _parse_text(value: object) -> str:
    if type(value) is str:
        result = value
    elif type(value) is list:
        parts: list[str] = []
        for part in value:
            if type(part) is str:
                parts.append(part)
            elif type(part) is dict and type(part.get("text")) is str:
                if any(type(key) is not str for key in part):
                    raise TelegramImportError("TELEGRAM_MESSAGE_TEXT_INVALID")
                parts.append(part["text"])
            else:
                raise TelegramImportError("TELEGRAM_MESSAGE_TEXT_INVALID")
        result = "".join(parts)
    else:
        raise TelegramImportError("TELEGRAM_MESSAGE_TEXT_INVALID")
    try:
        result.encode()
    except UnicodeEncodeError as exc:
        raise TelegramImportError("TELEGRAM_MESSAGE_TEXT_INVALID") from exc
    if len(result) > 20_000:
        raise TelegramImportError("TELEGRAM_MESSAGE_TEXT_INVALID")
    return result


def _parse_chat_id_argument(chat_id: str | None) -> int | None:
    if chat_id is None:
        return None
    if (
        not chat_id
        or len(chat_id) > len(str(MAX_IDENTITY_INTEGER))
        or not chat_id.isascii()
        or not chat_id.isdecimal()
    ):
        raise TelegramImportError("TELEGRAM_CHAT_ID_INVALID")
    parsed = int(chat_id)
    if parsed < 1 or parsed > MAX_IDENTITY_INTEGER:
        raise TelegramImportError("TELEGRAM_CHAT_ID_INVALID")
    return parsed


def _dialog_id(dialog: object) -> int:
    if type(dialog) is not dict:
        raise TelegramImportError("TELEGRAM_EXPORT_SCHEMA_UNSUPPORTED")
    return _parse_identifier(
        dialog.get("id"),
        reason="TELEGRAM_EXPORT_SCHEMA_UNSUPPORTED",
    )


def _select_dialog(
    export: object,
    requested_chat_id: int | None,
) -> tuple[dict[str, Any], str]:
    if type(export) is not dict or any(type(key) is not str for key in export):
        raise TelegramImportError("TELEGRAM_EXPORT_SCHEMA_UNSUPPORTED")

    if "messages" in export:
        if "chats" in export:
            raise TelegramImportError("TELEGRAM_EXPORT_SCHEMA_UNSUPPORTED")
        selected_id = _dialog_id(export)
        if requested_chat_id is not None and selected_id != requested_chat_id:
            raise TelegramImportError("TELEGRAM_CHAT_NOT_FOUND")
        return export, "single_chat"

    chats = export.get("chats")
    if type(chats) is not dict or any(type(key) is not str for key in chats):
        raise TelegramImportError("TELEGRAM_EXPORT_SCHEMA_UNSUPPORTED")
    dialogs = chats.get("list")
    if type(dialogs) is not list:
        raise TelegramImportError("TELEGRAM_EXPORT_SCHEMA_UNSUPPORTED")

    candidates: list[dict[str, Any]] = []
    for dialog in dialogs:
        dialog_id = _dialog_id(dialog)
        if requested_chat_id is None or requested_chat_id == dialog_id:
            candidates.append(dialog)
    if requested_chat_id is None and len(candidates) != 1:
        raise TelegramImportError("TELEGRAM_CHAT_SELECTION_REQUIRED")
    if not candidates:
        raise TelegramImportError("TELEGRAM_CHAT_NOT_FOUND")
    if len(candidates) != 1:
        raise TelegramImportError("TELEGRAM_CHAT_SELECTION_AMBIGUOUS")
    return candidates[0], "full_export"


def _parse_timed_metadata(
    message: dict[str, Any],
) -> tuple[int, str, str | None, str, int]:
    display_date = message.get("date")
    if type(display_date) is not str or not display_date or len(display_date) > 64:
        raise TelegramImportError("TELEGRAM_MESSAGE_TIME_INVALID")
    message_epoch, message_timestamp = _parse_epoch(
        message.get("date_unixtime"),
        reason="TELEGRAM_MESSAGE_TIME_INVALID",
    )
    has_edited = "edited" in message
    has_edited_epoch = "edited_unixtime" in message
    if has_edited != has_edited_epoch:
        raise TelegramImportError("TELEGRAM_EDIT_TIME_INVALID")
    if has_edited:
        edited_display = message["edited"]
        if type(edited_display) is not str or not edited_display or len(edited_display) > 64:
            raise TelegramImportError("TELEGRAM_EDIT_TIME_INVALID")
        edited_epoch, edited_timestamp = _parse_epoch(
            message["edited_unixtime"],
            reason="TELEGRAM_EDIT_TIME_INVALID",
        )
        if edited_epoch < message_epoch:
            raise TelegramImportError("TELEGRAM_EDIT_TIME_INVALID")
        revision = edited_epoch
        event_epoch = edited_epoch
        event_timestamp = edited_timestamp
    else:
        edited_timestamp = None
        revision = 0
        event_epoch = message_epoch
        event_timestamp = message_timestamp
    return (
        revision,
        message_timestamp,
        edited_timestamp,
        event_timestamp,
        event_epoch,
    )


def _parse_reply(message: dict[str, Any]) -> tuple[int | None, str | None]:
    reply_value = message.get("reply_to_message_id")
    reply_to_message_id = (
        None
        if reply_value is None
        else _parse_identifier(
            reply_value,
            reason="TELEGRAM_REPLY_ID_INVALID",
        )
    )
    reply_to_peer_value = message.get("reply_to_peer_id")
    if reply_to_peer_value is None:
        return reply_to_message_id, None
    if (
        reply_to_message_id is None
        or type(reply_to_peer_value) is not str
        or not reply_to_peer_value
        or len(reply_to_peer_value) > 128
    ):
        raise TelegramImportError("TELEGRAM_REPLY_ID_INVALID")
    try:
        reply_to_peer_value.encode()
    except UnicodeEncodeError as exc:
        raise TelegramImportError("TELEGRAM_REPLY_ID_INVALID") from exc
    return reply_to_message_id, reply_to_peer_value


def _skipped_message(
    message: dict[str, Any],
    *,
    source: Source,
    channel_id: str,
    message_id: int,
    revision: int | None,
    message_timestamp: str | None,
    edited_timestamp: str | None,
    event_timestamp: str | None,
    event_epoch: int | None,
    reply_to_message_id: int | None,
    reply_to_peer_id: str | None,
    skip_reason: str,
) -> HistoricalSkippedMessage:
    import_payload_hash = _canonical_hash(
        {
            "channel_id": channel_id,
            "kind": "SKIPPED_METADATA",
            "message": message,
            "skip_reason": skip_reason,
            "source": source.value,
        },
        reason="TELEGRAM_MESSAGE_INVALID",
    )
    return HistoricalSkippedMessage(
        source=source,
        channel_id=channel_id,
        message_id=message_id,
        revision=revision,
        message_timestamp=message_timestamp,
        edited_timestamp=edited_timestamp,
        event_timestamp=event_timestamp,
        event_epoch=event_epoch,
        reply_to_message_id=reply_to_message_id,
        reply_to_peer_id=reply_to_peer_id,
        skip_reason=skip_reason,
        import_payload_hash=import_payload_hash,
    )


def _historical_message(
    message: dict[str, Any],
    *,
    source: Source,
    channel_id: str,
) -> HistoricalRecord:
    message_type = message.get("type")
    if type(message_type) is not str:
        raise TelegramImportError("TELEGRAM_MESSAGE_INVALID")
    message_id = _parse_identifier(
        message.get("id"),
        reason="TELEGRAM_MESSAGE_ID_INVALID",
    )
    if message_type not in {"message", *SKIPPED_MESSAGE_TYPES}:
        raise TelegramImportError("TELEGRAM_MESSAGE_TYPE_UNSUPPORTED")

    has_date = "date" in message
    has_date_epoch = "date_unixtime" in message
    if message_type == "unsupported" and not has_date and not has_date_epoch:
        if "edited" in message or "edited_unixtime" in message:
            raise TelegramImportError("TELEGRAM_EDIT_TIME_INVALID")
        reply_to_message_id, reply_to_peer_id = _parse_reply(message)
        return _skipped_message(
            message,
            source=source,
            channel_id=channel_id,
            message_id=message_id,
            revision=None,
            message_timestamp=None,
            edited_timestamp=None,
            event_timestamp=None,
            event_epoch=None,
            reply_to_message_id=reply_to_message_id,
            reply_to_peer_id=reply_to_peer_id,
            skip_reason="TELEGRAM_UNSUPPORTED_RECORD",
        )
    if has_date != has_date_epoch:
        raise TelegramImportError("TELEGRAM_MESSAGE_TIME_INVALID")

    (
        revision,
        message_timestamp,
        edited_timestamp,
        event_timestamp,
        event_epoch,
    ) = _parse_timed_metadata(message)
    reply_to_message_id, reply_to_peer_id = _parse_reply(message)
    if message_type == "unsupported":
        return _skipped_message(
            message,
            source=source,
            channel_id=channel_id,
            message_id=message_id,
            revision=revision,
            message_timestamp=message_timestamp,
            edited_timestamp=edited_timestamp,
            event_timestamp=event_timestamp,
            event_epoch=event_epoch,
            reply_to_message_id=reply_to_message_id,
            reply_to_peer_id=reply_to_peer_id,
            skip_reason="TELEGRAM_UNSUPPORTED_RECORD",
        )
    if message_type != "message":
        return _skipped_message(
            message,
            source=source,
            channel_id=channel_id,
            message_id=message_id,
            revision=revision,
            message_timestamp=message_timestamp,
            edited_timestamp=edited_timestamp,
            event_timestamp=event_timestamp,
            event_epoch=event_epoch,
            reply_to_message_id=reply_to_message_id,
            reply_to_peer_id=reply_to_peer_id,
            skip_reason="TELEGRAM_SERVICE_RECORD",
        )

    has_text = "text" in message
    has_rich_message = "rich_message" in message
    if has_rich_message:
        if has_text or type(message["rich_message"]) is not dict:
            raise TelegramImportError("TELEGRAM_MESSAGE_INVALID")
        return _skipped_message(
            message,
            source=source,
            channel_id=channel_id,
            message_id=message_id,
            revision=revision,
            message_timestamp=message_timestamp,
            edited_timestamp=edited_timestamp,
            event_timestamp=event_timestamp,
            event_epoch=event_epoch,
            reply_to_message_id=reply_to_message_id,
            reply_to_peer_id=reply_to_peer_id,
            skip_reason="TELEGRAM_RICH_MESSAGE",
        )
    if not has_text:
        raise TelegramImportError("TELEGRAM_MESSAGE_TEXT_INVALID")
    text = _parse_text(message["text"])
    if not text.strip():
        return _skipped_message(
            message,
            source=source,
            channel_id=channel_id,
            message_id=message_id,
            revision=revision,
            message_timestamp=message_timestamp,
            edited_timestamp=edited_timestamp,
            event_timestamp=event_timestamp,
            event_epoch=event_epoch,
            reply_to_message_id=reply_to_message_id,
            reply_to_peer_id=reply_to_peer_id,
            skip_reason="TELEGRAM_BLANK_TEXT",
        )

    envelope: dict[str, str | int] = {
        "channel_id": channel_id,
        "message_id": message_id,
        "revision": revision,
        "source": source.value,
        "text": text,
        "timestamp": event_timestamp,
    }
    try:
        parse_envelope(envelope)
    except EnvelopeError as exc:
        raise TelegramImportError("TELEGRAM_MESSAGE_NOT_REPLAYABLE") from exc

    import_payload_hash = _canonical_hash(
        {
            "edited_timestamp": edited_timestamp,
            "envelope": envelope,
            "message_timestamp": message_timestamp,
            "reply_to_message_id": reply_to_message_id,
            "reply_to_peer_id": reply_to_peer_id,
        },
        reason="TELEGRAM_MESSAGE_TEXT_INVALID",
    )

    return HistoricalMessage(
        source=source,
        channel_id=channel_id,
        message_id=message_id,
        revision=revision,
        message_timestamp=message_timestamp,
        edited_timestamp=edited_timestamp,
        event_timestamp=event_timestamp,
        event_epoch=event_epoch,
        reply_to_message_id=reply_to_message_id,
        reply_to_peer_id=reply_to_peer_id,
        text=text,
        import_payload_hash=import_payload_hash,
    )


def parse_telegram_export(
    export: object,
    *,
    source: Source,
    chat_id: str | None = None,
) -> ImportBatch:
    requested_chat_id = _parse_chat_id_argument(chat_id)
    dialog, input_shape = _select_dialog(export, requested_chat_id)
    dialog_type = dialog.get("type")
    if type(dialog_type) is not str or dialog_type not in SUPPORTED_CHANNEL_TYPES:
        raise TelegramImportError("TELEGRAM_CHAT_TYPE_UNSUPPORTED")
    selected_id = _dialog_id(dialog)
    messages = dialog.get("messages")
    if type(messages) is not list or len(messages) > MAX_EXPORT_MESSAGES:
        raise TelegramImportError("TELEGRAM_EXPORT_LIMIT_EXCEEDED")

    channel_id = str(selected_id)
    records: list[HistoricalMessage] = []
    skipped_records: list[HistoricalSkippedMessage] = []
    exact_duplicates = 0
    seen: dict[tuple[str, str, str, str], str] = {}
    for raw_message in messages:
        if type(raw_message) is not dict or any(type(key) is not str for key in raw_message):
            raise TelegramImportError("TELEGRAM_MESSAGE_INVALID")
        record = _historical_message(raw_message, source=source, channel_id=channel_id)
        prior_hash = seen.get(record.db_identity)
        if prior_hash is not None:
            if prior_hash != record.import_payload_hash:
                raise TelegramImportError("TELEGRAM_REVISION_CONFLICT")
            exact_duplicates += 1
            continue
        seen[record.db_identity] = record.import_payload_hash
        if isinstance(record, HistoricalSkippedMessage):
            skipped_records.append(record)
        else:
            records.append(record)

    records.sort(key=lambda record: record.sort_key)
    skipped_records.sort(key=lambda record: record.stable_key)
    return ImportBatch(
        records=tuple(records),
        skipped_records=tuple(skipped_records),
        input_shape=input_shape,
        source=source,
        chat_id=channel_id,
        input_messages=len(messages),
        exact_export_duplicates=exact_duplicates,
    )


def load_telegram_export(
    path: str | Path,
    *,
    source: Source,
    chat_id: str | None = None,
) -> ImportBatch:
    input_path = Path(path)
    try:
        input_stat = input_path.stat()
        if (
            input_path.is_symlink()
            or not stat.S_ISREG(input_stat.st_mode)
            or input_stat.st_size > MAX_EXPORT_BYTES
        ):
            raise TelegramImportError("TELEGRAM_EXPORT_LIMIT_EXCEEDED")
        with input_path.open("rb") as stream:
            raw = stream.read(MAX_EXPORT_BYTES + 1)
        if len(raw) > MAX_EXPORT_BYTES:
            raise TelegramImportError("TELEGRAM_EXPORT_LIMIT_EXCEEDED")
        text = raw.decode()
        export = json.loads(
            text,
            object_pairs_hook=_closed_json_object,
            parse_constant=_reject_json_constant,
            parse_float=_bounded_json_float,
            parse_int=_bounded_json_integer,
        )
    except TelegramImportError:
        raise
    except (
        DuplicateJsonKey,
        InvalidJsonNumber,
        UnicodeDecodeError,
        ValueError,
        RecursionError,
    ) as exc:
        raise TelegramImportError("TELEGRAM_EXPORT_INVALID_JSON") from exc
    except OSError as exc:
        raise TelegramImportError("TELEGRAM_EXPORT_READ_ERROR") from exc
    return parse_telegram_export(export, source=source, chat_id=chat_id)


def render_internal_jsonl(batch: ImportBatch) -> str:
    return "".join(
        json.dumps(
            record.envelope,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
        for record in batch.records
    )


class HistoricalJournal(Journal):
    def __init__(self, path: str | Path, config_fingerprint: str) -> None:
        super().__init__(path, config_fingerprint)
        self.connection.executescript(HISTORICAL_IMPORT_SCHEMA)

    def __enter__(self) -> Self:
        return self

    @contextmanager
    def transaction(self) -> Iterator[None]:
        if not self.connection.in_transaction:
            with super().transaction():
                yield
            return
        self.connection.execute("SAVEPOINT historical_event")
        try:
            yield
        except BaseException:
            self.connection.execute("ROLLBACK TO SAVEPOINT historical_event")
            self.connection.execute("RELEASE SAVEPOINT historical_event")
            raise
        else:
            self.connection.execute("RELEASE SAVEPOINT historical_event")

    @contextmanager
    def import_transaction(self) -> Iterator[None]:
        if self.connection.in_transaction:
            raise RuntimeError("IMPORT_TRANSACTION_ALREADY_ACTIVE")
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self.connection.execute("ROLLBACK")
            raise
        else:
            self.connection.execute("COMMIT")

    def import_hashes(
        self,
        batch: ImportBatch,
    ) -> dict[tuple[str, str, str, str], tuple[str, str]]:
        event_rows = self.connection.execute(
            """
            SELECT message_id, revision, import_payload_hash
            FROM telegram_import_events
            WHERE source = ? AND channel_key = ?
            """,
            (batch.source.value, batch.chat_key),
        ).fetchall()
        skipped_rows = self.connection.execute(
            """
            SELECT message_id, revision, import_payload_hash
            FROM telegram_import_skipped
            WHERE source = ? AND channel_key = ?
            """,
            (batch.source.value, batch.chat_key),
        ).fetchall()
        result: dict[tuple[str, str, str, str], tuple[str, str]] = {}
        for kind, rows in (
            ("event", event_rows),
            ("skipped", skipped_rows),
        ):
            for row in rows:
                identity = (
                    batch.source.value,
                    batch.chat_key,
                    str(row["message_id"]),
                    str(row["revision"]),
                )
                if identity in result:
                    raise TelegramImportError("TELEGRAM_IMPORT_STATE_INVALID")
                result[identity] = (kind, str(row["import_payload_hash"]))
        return result

    def validate_provenance(self) -> None:
        orphan = self.connection.execute(
            """
            SELECT 1
            FROM events AS event
            LEFT JOIN telegram_import_events AS imported
              ON imported.source = event.source
             AND imported.channel_key = event.channel_key
             AND imported.message_id = event.message_id
             AND imported.revision = event.revision
            WHERE imported.source IS NULL
            LIMIT 1
            """
        ).fetchone()
        if orphan is not None:
            raise TelegramImportError("TELEGRAM_DATABASE_PROVENANCE_MISMATCH")

        maximum = self.connection.execute(
            """
            SELECT event_epoch, source, channel_key, message_id, revision,
                   import_payload_hash
            FROM (
                SELECT event_epoch, source, channel_key, message_id, revision,
                       import_payload_hash
                FROM telegram_import_events
                UNION ALL
                SELECT event_epoch, source, channel_key, message_id, revision,
                       import_payload_hash
                FROM telegram_import_skipped
                WHERE event_epoch IS NOT NULL
            ) AS timed
            ORDER BY event_epoch DESC,
                     source DESC,
                     channel_key DESC,
                     CAST(message_id AS INTEGER) DESC,
                     CAST(revision AS INTEGER) DESC,
                     import_payload_hash DESC
            LIMIT 1
            """
        ).fetchone()
        persisted = (
            None
            if maximum is None
            else (
                int(maximum["event_epoch"]),
                str(maximum["source"]),
                str(maximum["channel_key"]),
                int(maximum["message_id"]),
                int(maximum["revision"]),
                str(maximum["import_payload_hash"]),
            )
        )
        if persisted != self.event_time_watermark():
            raise TelegramImportError("TELEGRAM_IMPORT_STATE_INVALID")

    def event_time_watermark(self) -> EventSortKey | None:
        row = self.connection.execute(
            """
            SELECT event_epoch, source, channel_key, message_id, revision,
                   import_payload_hash
            FROM telegram_import_state
            WHERE singleton = 1
            """
        ).fetchone()
        if row is None:
            return None
        return (
            int(row["event_epoch"]),
            str(row["source"]),
            str(row["channel_key"]),
            int(row["message_id"]),
            int(row["revision"]),
            str(row["import_payload_hash"]),
        )

    def set_event_time_watermark(self, record: HistoricalRecord) -> None:
        sort_key = record.sort_key
        if sort_key is None:
            raise RuntimeError("TIMELESS_RECORD_CANNOT_ADVANCE_WATERMARK")
        (
            event_epoch,
            source,
            channel_key,
            message_id,
            revision,
            import_payload_hash,
        ) = sort_key
        self.connection.execute(
            """
            INSERT INTO telegram_import_state (
                singleton, event_epoch, source, channel_key, message_id,
                revision, import_payload_hash
            ) VALUES (1, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (singleton) DO UPDATE SET
                event_epoch = excluded.event_epoch,
                source = excluded.source,
                channel_key = excluded.channel_key,
                message_id = excluded.message_id,
                revision = excluded.revision,
                import_payload_hash = excluded.import_payload_hash
            """,
            (
                event_epoch,
                source,
                channel_key,
                str(message_id),
                str(revision),
                import_payload_hash,
            ),
        )

    def insert_import_record(self, record: HistoricalMessage) -> None:
        self.connection.execute(
            """
            INSERT INTO telegram_import_events (
                source, channel_key, message_id, revision,
                message_timestamp, edited_timestamp, event_timestamp, event_epoch,
                reply_to_message_id, reply_to_peer_key, import_payload_hash, export_format
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'TELEGRAM_DESKTOP_JSON')
            """,
            (
                *record.db_identity,
                record.message_timestamp,
                record.edited_timestamp,
                record.event_timestamp,
                record.event_epoch,
                (
                    None
                    if record.reply_to_message_id is None
                    else str(record.reply_to_message_id)
                ),
                record.reply_to_peer_key,
                record.import_payload_hash,
            ),
        )

    def insert_skipped_record(self, record: HistoricalSkippedMessage) -> None:
        self.connection.execute(
            """
            INSERT INTO telegram_import_skipped (
                source, channel_key, message_id, revision,
                message_timestamp, edited_timestamp, event_timestamp, event_epoch,
                reply_to_message_id, reply_to_peer_key, skip_reason,
                import_payload_hash, export_format
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'TELEGRAM_DESKTOP_JSON')
            """,
            (
                *record.db_identity,
                record.message_timestamp,
                record.edited_timestamp,
                record.event_timestamp,
                record.event_epoch,
                (
                    None
                    if record.reply_to_message_id is None
                    else str(record.reply_to_message_id)
                ),
                record.reply_to_peer_key,
                record.skip_reason,
                record.import_payload_hash,
            ),
        )

    def import_counts(self) -> tuple[int, int]:
        event_row = self.connection.execute(
            "SELECT COUNT(*) AS count FROM telegram_import_events"
        ).fetchone()
        skipped_row = self.connection.execute(
            "SELECT COUNT(*) AS count FROM telegram_import_skipped"
        ).fetchone()
        assert event_row is not None and skipped_row is not None
        return int(event_row["count"]), int(skipped_row["count"])


def _conflict_outcome(record: HistoricalMessage) -> Outcome:
    event = parse_envelope(record.envelope)
    return Outcome(
        disposition="conflict",
        reason="TELEGRAM_REVISION_CONFLICT",
        journaled=False,
        event_identity=event.identity_text,
    )


def _load_import_batches(
    input_paths: Sequence[str | Path],
    config: MvpConfig,
    *,
    sources: Sequence[Source],
    chat_id: str | None = None,
) -> tuple[ImportBatch, ...]:
    if (
        not sources
        or len(sources) > len(Source)
        or len(set(sources)) != len(sources)
        or len(input_paths) not in {1, len(sources)}
        or (chat_id is not None and len(sources) != 1)
    ):
        raise TelegramImportError("TELEGRAM_IMPORT_ARGUMENTS_INVALID")

    paths = (
        tuple(input_paths) * len(sources)
        if len(input_paths) == 1
        else tuple(input_paths)
    )
    batches: list[ImportBatch] = []
    for input_path, source in zip(paths, sources, strict=True):
        requested_chat_id = (
            chat_id
            if chat_id is not None
            else (config.channel_for(source) if len(sources) > 1 else None)
        )
        batch = load_telegram_export(
            input_path,
            source=source,
            chat_id=requested_chat_id,
        )
        if batch.chat_id != config.channel_for(source):
            raise TelegramImportError("TELEGRAM_SOURCE_CHANNEL_NOT_ALLOWED")
        batches.append(batch)
    return tuple(batches)


def _run_import_batches(
    batches: Sequence[ImportBatch],
    config: MvpConfig,
    db_path: str | Path,
) -> dict[str, Any]:
    records = sorted(
        (record for batch in batches for record in batch.records),
        key=lambda record: record.sort_key,
    )
    skipped_records = sorted(
        (record for batch in batches for record in batch.skipped_records),
        key=lambda record: record.stable_key,
    )
    timed_records: list[HistoricalRecord] = [
        *records,
        *(record for record in skipped_records if record.sort_key is not None),
    ]
    timed_records.sort(key=lambda record: record.sort_key)

    outcomes: list[dict[str, Any]] = []
    counters = {"accepted": 0, "conflict": 0, "duplicate": 0, "rejected": 0}
    skipped_duplicates = 0
    with HistoricalJournal(db_path, config.fingerprint) as journal:
        service = OfflineSignalService(config, journal)
        with journal.import_transaction():
            journal.validate_provenance()
            existing_hashes: dict[
                tuple[str, str, str, str],
                tuple[str, str],
            ] = {}
            for batch in batches:
                batch_hashes = journal.import_hashes(batch)
                if existing_hashes.keys() & batch_hashes.keys():
                    raise TelegramImportError("TELEGRAM_IMPORT_STATE_INVALID")
                existing_hashes.update(batch_hashes)

            for record in skipped_records:
                existing = existing_hashes.get(record.db_identity)
                if existing is not None and existing != (
                    "skipped",
                    record.import_payload_hash,
                ):
                    raise TelegramImportError("TELEGRAM_REVISION_CONFLICT")

            watermark = journal.event_time_watermark()
            unseen = [
                record
                for record in timed_records
                if record.db_identity not in existing_hashes
            ]
            if watermark is not None and any(
                record.sort_key is not None and record.sort_key <= watermark
                for record in unseen
            ):
                raise TelegramImportError("TELEGRAM_EVENT_TIME_REGRESSION")

            new_timed_records: list[HistoricalRecord] = []
            for event_order, record in enumerate(records, start=1):
                existing = existing_hashes.get(record.db_identity)
                if existing is not None and existing != (
                    "event",
                    record.import_payload_hash,
                ):
                    outcome = _conflict_outcome(record)
                else:
                    outcome = service.process_mapping(record.envelope)
                    if existing is None and outcome.disposition != "conflict":
                        journal.insert_import_record(record)
                        new_timed_records.append(record)
                counters[outcome.disposition] += 1
                rendered = outcome.as_dict()
                rendered["event_order"] = event_order
                outcomes.append(rendered)

            for record in skipped_records:
                existing = existing_hashes.get(record.db_identity)
                if existing is not None:
                    skipped_duplicates += 1
                    continue
                journal.insert_skipped_record(record)
                if record.sort_key is not None:
                    new_timed_records.append(record)

            if new_timed_records:
                journal.set_event_time_watermark(
                    max(
                        new_timed_records,
                        key=lambda record: record.sort_key,
                    )
                )
        setups, intents = journal.counts()
        imported, imported_skipped = journal.import_counts()

    chat_keys = {
        batch.source.value: batch.chat_key
        for batch in sorted(batches, key=lambda item: item.source.value)
    }
    input_shapes = {
        batch.source.value: batch.input_shape
        for batch in sorted(batches, key=lambda item: item.source.value)
    }
    result: dict[str, Any] = {
        "accepted": counters["accepted"],
        "chat_keys": chat_keys,
        "config_fingerprint": config.fingerprint,
        "conflicts": counters["conflict"],
        "duplicates": counters["duplicate"],
        "exact_export_duplicates": sum(
            batch.exact_export_duplicates for batch in batches
        ),
        "imported_messages": imported,
        "imported_skipped_messages": imported_skipped,
        "input_format": "TELEGRAM_DESKTOP_JSON",
        "input_messages": sum(batch.input_messages for batch in batches),
        "input_shapes": input_shapes,
        "intents": intents,
        "outcomes": outcomes,
        "rejected": counters["rejected"],
        "selected_channels": len(batches),
        "selected_messages": len(records),
        "setups": setups,
        "skipped_duplicates": skipped_duplicates,
        "skipped_messages": len(skipped_records),
        "sources": sorted(batch.source.value for batch in batches),
        "stage": "OFFLINE_SIMULATION",
    }
    if len(batches) == 1:
        result["chat_key"] = batches[0].chat_key
        result["input_shape"] = batches[0].input_shape
    return result


def run_historical_replays_with_config(
    input_paths: Sequence[str | Path],
    config: MvpConfig,
    db_path: str | Path,
    *,
    sources: Sequence[Source],
    chat_id: str | None = None,
) -> dict[str, Any]:
    batches = _load_import_batches(
        input_paths,
        config,
        sources=sources,
        chat_id=chat_id,
    )
    return _run_import_batches(batches, config, db_path)


def run_historical_replay_with_config(
    input_path: str | Path,
    config: MvpConfig,
    db_path: str | Path,
    *,
    source: Source,
    chat_id: str | None = None,
) -> dict[str, Any]:
    return run_historical_replays_with_config(
        (input_path,),
        config,
        db_path,
        sources=(source,),
        chat_id=chat_id,
    )


def run_historical_replays(
    input_paths: Sequence[str | Path],
    config_path: str | Path,
    db_path: str | Path,
    *,
    sources: Sequence[Source],
    chat_id: str | None = None,
) -> dict[str, Any]:
    config = load_config(config_path)
    return run_historical_replays_with_config(
        input_paths,
        config,
        db_path,
        sources=sources,
        chat_id=chat_id,
    )


def run_historical_replay(
    input_path: str | Path,
    config_path: str | Path,
    db_path: str | Path,
    *,
    source: Source,
    chat_id: str | None = None,
) -> dict[str, Any]:
    return run_historical_replays(
        (input_path,),
        config_path,
        db_path,
        sources=(source,),
        chat_id=chat_id,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 -m tradebot_mvp.telegram_import")
    parser.add_argument(
        "--input",
        action="append",
        required=True,
        help="repeat for source-aligned per-chat exports; one full export may be shared",
    )
    parser.add_argument(
        "--source",
        action="append",
        required=True,
        choices=[source.value for source in Source],
        help="repeat once to import both fixed configured sources",
    )
    parser.add_argument("--chat-id", help="single-source override; must match config")
    parser.add_argument("--config", required=True)
    parser.add_argument("--db", required=True)
    return parser


def _error(reason: str) -> int:
    sys.stdout.write(
        json.dumps(
            {"reason": reason, "status": "ERROR"},
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = run_historical_replays(
            args.input,
            args.config,
            args.db,
            sources=tuple(Source(source) for source in args.source),
            chat_id=args.chat_id,
        )
    except TelegramImportError as exc:
        return _error(exc.reason)
    except ConfigFingerprintMismatch:
        return _error("CONFIG_FINGERPRINT_MISMATCH")
    except ConfigError as exc:
        return _error(exc.reason)
    except (
        OSError,
        sqlite3.Error,
        UnicodeDecodeError,
        UnicodeEncodeError,
        ValueError,
        OverflowError,
    ):
        return _error("INPUT_OR_DATABASE_ERROR")
    sys.stdout.write(render_summary(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
