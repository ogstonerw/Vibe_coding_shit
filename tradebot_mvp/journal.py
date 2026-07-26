from __future__ import annotations

import json
import os
import sqlite3
import stat
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .contracts import RawMessage, Signal, SimulatedLimitIntent, decimal_text


class ConfigFingerprintMismatch(RuntimeError):
    reason = "CONFIG_FINGERPRINT_MISMATCH"


SCHEMA = """
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS events (
    source TEXT NOT NULL,
    channel_key TEXT NOT NULL,
    message_id TEXT NOT NULL,
    revision TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    disposition TEXT NOT NULL CHECK (disposition IN ('accepted', 'rejected')),
    reason TEXT NOT NULL,
    PRIMARY KEY (source, channel_key, message_id, revision)
) STRICT;

CREATE TABLE IF NOT EXISTS setups (
    setup_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    channel_key TEXT NOT NULL,
    message_id TEXT NOT NULL,
    revision TEXT NOT NULL,
    symbol TEXT NOT NULL CHECK (symbol = 'BTCUSDT'),
    side TEXT NOT NULL CHECK (side IN ('LONG', 'SHORT')),
    entry_text TEXT NOT NULL,
    stop_text TEXT NOT NULL,
    local_status TEXT NOT NULL CHECK (local_status = 'ACTIVE'),
    UNIQUE (source, channel_key, message_id, revision),
    FOREIGN KEY (source, channel_key, message_id, revision)
        REFERENCES events (source, channel_key, message_id, revision)
) STRICT;

CREATE TABLE IF NOT EXISTS intents (
    intent_id TEXT PRIMARY KEY,
    setup_id TEXT NOT NULL UNIQUE,
    order_type TEXT NOT NULL CHECK (order_type = 'LIMIT'),
    stage TEXT NOT NULL CHECK (stage = 'OFFLINE_SIMULATION'),
    simulated INTEGER NOT NULL CHECK (simulated = 1),
    symbol TEXT NOT NULL CHECK (symbol = 'BTCUSDT'),
    side TEXT NOT NULL CHECK (side IN ('LONG', 'SHORT')),
    entry_text TEXT NOT NULL,
    stop_text TEXT NOT NULL,
    quantity_text TEXT NOT NULL,
    risk_budget_text TEXT NOT NULL,
    risk_amount_text TEXT NOT NULL,
    notional_text TEXT NOT NULL,
    FOREIGN KEY (setup_id) REFERENCES setups (setup_id)
) STRICT;

CREATE TABLE IF NOT EXISTS journal_events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    channel_key TEXT NOT NULL,
    message_id TEXT NOT NULL,
    revision TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    FOREIGN KEY (source, channel_key, message_id, revision)
        REFERENCES events (source, channel_key, message_id, revision)
) STRICT;
"""


class Journal:
    def __init__(self, path: str | Path, config_fingerprint: str) -> None:
        self.path = str(path)
        self._prepare_path()
        self.connection = sqlite3.connect(self.path, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.execute("PRAGMA synchronous = FULL")
        self.connection.executescript(SCHEMA)
        self._secure_files()
        self._bind_config(config_fingerprint)

    def close(self) -> None:
        self._secure_files()
        self.connection.close()

    def _prepare_path(self) -> None:
        if self.path == ":memory:":
            return
        database_path = Path(self.path)
        candidates = (database_path, Path(self.path + "-wal"), Path(self.path + "-shm"))
        for candidate in candidates:
            if candidate.exists() and (
                candidate.is_symlink() or not stat.S_ISREG(candidate.lstat().st_mode)
            ):
                raise OSError("UNSAFE_DATABASE_PATH")
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(database_path, flags, 0o600)
        os.close(descriptor)
        os.chmod(database_path, 0o600)

    def _secure_files(self) -> None:
        if self.path == ":memory:":
            return
        for candidate in (Path(self.path), Path(self.path + "-wal"), Path(self.path + "-shm")):
            if candidate.exists() and not candidate.is_symlink():
                os.chmod(candidate, 0o600)

    def __enter__(self) -> Journal:
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()

    def _bind_config(self, fingerprint: str) -> None:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            row = self.connection.execute(
                "SELECT value FROM metadata WHERE key = 'config_fingerprint'"
            ).fetchone()
            if row is None:
                self.connection.execute(
                    "INSERT INTO metadata (key, value) VALUES ('config_fingerprint', ?)",
                    (fingerprint,),
                )
            elif row["value"] != fingerprint:
                raise ConfigFingerprintMismatch()
            self.connection.execute("COMMIT")
        except BaseException:
            self.connection.execute("ROLLBACK")
            self.close()
            raise

    @contextmanager
    def transaction(self) -> Iterator[None]:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self.connection.execute("ROLLBACK")
            self._secure_files()
            raise
        else:
            self.connection.execute("COMMIT")
            self._secure_files()

    def existing_event(self, event: RawMessage) -> sqlite3.Row | None:
        return self.connection.execute(
            """
            SELECT payload_hash, disposition, reason
            FROM events
            WHERE source = ? AND channel_key = ? AND message_id = ? AND revision = ?
            """,
            event.db_identity,
        ).fetchone()

    def insert_event(self, event: RawMessage, disposition: str, reason: str) -> None:
        self.connection.execute(
            """
            INSERT INTO events (
                source, channel_key, message_id, revision, timestamp,
                payload_hash, disposition, reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                *event.db_identity,
                event.timestamp,
                event.payload_hash,
                disposition,
                reason,
            ),
        )

    def insert_setup(self, setup_id: str, event: RawMessage, signal: Signal) -> None:
        self.connection.execute(
            """
            INSERT INTO setups (
                setup_id, source, channel_key, message_id, revision,
                symbol, side, entry_text, stop_text, local_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
            """,
            (
                setup_id,
                *event.db_identity,
                signal.symbol,
                signal.side.value,
                decimal_text(signal.entry),
                decimal_text(signal.stop),
            ),
        )

    def insert_intent(self, intent: SimulatedLimitIntent) -> None:
        self.connection.execute(
            """
            INSERT INTO intents (
                intent_id, setup_id, order_type, stage, simulated,
                symbol, side, entry_text, stop_text, quantity_text,
                risk_budget_text, risk_amount_text, notional_text
            ) VALUES (?, ?, 'LIMIT', 'OFFLINE_SIMULATION', 1, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                intent.intent_id,
                intent.setup_id,
                intent.symbol,
                intent.side.value,
                decimal_text(intent.entry),
                decimal_text(intent.stop),
                decimal_text(intent.quantity),
                decimal_text(intent.risk_budget),
                decimal_text(intent.risk_amount),
                decimal_text(intent.notional),
            ),
        )

    def append_journal(self, event: RawMessage, event_type: str, payload: dict[str, Any]) -> None:
        payload_json = json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        self.connection.execute(
            """
            INSERT INTO journal_events (
                source, channel_key, message_id, revision, event_type, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (*event.db_identity, event_type, payload_json),
        )

    def active_setup_count(self) -> int:
        row = self.connection.execute(
            "SELECT COUNT(*) AS count FROM setups WHERE local_status = 'ACTIVE'"
        ).fetchone()
        assert row is not None
        return int(row["count"])

    def counts(self) -> tuple[int, int]:
        setup_row = self.connection.execute("SELECT COUNT(*) AS count FROM setups").fetchone()
        intent_row = self.connection.execute("SELECT COUNT(*) AS count FROM intents").fetchone()
        assert setup_row is not None and intent_row is not None
        return int(setup_row["count"]), int(intent_row["count"])

    def event_count(self) -> int:
        row = self.connection.execute("SELECT COUNT(*) AS count FROM events").fetchone()
        assert row is not None
        return int(row["count"])
