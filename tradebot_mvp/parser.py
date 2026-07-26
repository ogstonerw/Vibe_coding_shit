from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from .config import DECIMAL_RE
from .contracts import RawMessage, Side, Signal, Source, decimal_text


EVENT_FIELDS = {
    "channel_id",
    "message_id",
    "revision",
    "source",
    "text",
    "timestamp",
}
UTC_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
HEADER_RE = re.compile(r"([A-Z0-9А-ЯЁ]+)\s+(LONG|ЛОНГ|SHORT|ШОРТ)\Z")
ENTRY_RE = re.compile(r"(?:ENTRY|ВХОД)\s+(.+)\Z")
STOP_RE = re.compile(r"(?:STOP|СТОП)\s+(.+)\Z")
AMBIGUOUS_STOP_RE = re.compile(r"(?:STOP|СТОП)\s+(?:UNDER|ABOVE|ПОД|НАД)\b")
RISK_RE = re.compile(r"(?:RISK|РИСК)\b")
MAX_IDENTITY_INTEGER = 2**63 - 1


class EnvelopeError(ValueError):
    def __init__(self, reason: str = "INVALID_EVENT_ENVELOPE") -> None:
        super().__init__(reason)
        self.reason = reason


class SignalError(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def parse_envelope(data: Any) -> RawMessage:
    if type(data) is not dict or set(data) != EVENT_FIELDS:
        raise EnvelopeError()
    if any(type(key) is not str for key in data):
        raise EnvelopeError()

    source_value = data["source"]
    if type(source_value) is not str:
        raise EnvelopeError()
    try:
        source = Source(source_value)
    except ValueError as exc:
        raise EnvelopeError() from exc

    channel_id = data["channel_id"]
    text = data["text"]
    timestamp = data["timestamp"]
    message_id = data["message_id"]
    revision = data["revision"]
    if type(channel_id) is not str or not channel_id or len(channel_id) > 128:
        raise EnvelopeError()
    if type(text) is not str or not text.strip() or len(text) > 20_000:
        raise EnvelopeError()
    if type(message_id) is not int or message_id < 0 or message_id > MAX_IDENTITY_INTEGER:
        raise EnvelopeError()
    if type(revision) is not int or revision < 0 or revision > MAX_IDENTITY_INTEGER:
        raise EnvelopeError()
    if type(timestamp) is not str or not UTC_RE.fullmatch(timestamp):
        raise EnvelopeError()
    try:
        datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise EnvelopeError() from exc

    try:
        canonical = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        payload_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    except UnicodeEncodeError as exc:
        raise EnvelopeError() from exc
    return RawMessage(
        source=source,
        channel_id=channel_id,
        message_id=message_id,
        revision=revision,
        timestamp=timestamp,
        text=text,
        payload_hash=payload_hash,
    )


def _parse_signal_decimal(raw: str) -> Decimal:
    if not DECIMAL_RE.fullmatch(raw):
        raise SignalError("INVALID_SIGNAL_DECIMAL")
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise SignalError("INVALID_SIGNAL_DECIMAL") from exc
    if not value.is_finite() or value <= 0:
        raise SignalError("INVALID_SIGNAL_DECIMAL")
    return value


def parse_signal(text: str) -> Signal:
    lines = [line.strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    lines = [line for line in lines if line]

    symbol: str | None = None
    side: Side | None = None
    entry: Decimal | None = None
    stop: Decimal | None = None

    for original_line in lines:
        line = original_line.upper()
        if AMBIGUOUS_STOP_RE.match(line):
            raise SignalError("STOP_PROFILE_UNRESOLVED")
        if RISK_RE.match(line):
            continue

        header = HEADER_RE.fullmatch(line)
        if header:
            if symbol is not None or side is not None:
                raise SignalError("DUPLICATE_SIGNAL_FIELD")
            raw_symbol, raw_side = header.groups()
            if raw_symbol in {"BTC", "BTCUSDT"}:
                symbol = "BTCUSDT"
            else:
                raise SignalError("SYMBOL_NOT_ALLOWED")
            side = Side.LONG if raw_side in {"LONG", "ЛОНГ"} else Side.SHORT
            continue

        entry_match = ENTRY_RE.fullmatch(line)
        if entry_match:
            if entry is not None:
                raise SignalError("DUPLICATE_SIGNAL_FIELD")
            entry = _parse_signal_decimal(entry_match.group(1))
            continue

        stop_match = STOP_RE.fullmatch(line)
        if stop_match:
            if stop is not None:
                raise SignalError("DUPLICATE_SIGNAL_FIELD")
            stop = _parse_signal_decimal(stop_match.group(1))
            continue

        raise SignalError("UNSUPPORTED_SIGNAL_GRAMMAR")

    if symbol is None or side is None:
        raise SignalError("MISSING_SYMBOL_OR_SIDE")
    if entry is None:
        raise SignalError("MISSING_ENTRY")
    if stop is None:
        raise SignalError("MISSING_STOP")
    if side is Side.LONG and stop >= entry:
        raise SignalError("INVALID_LONG_STOP_GEOMETRY")
    if side is Side.SHORT and stop <= entry:
        raise SignalError("INVALID_SHORT_STOP_GEOMETRY")

    normalized = json.dumps(
        {
            "entry": decimal_text(entry),
            "side": side.value,
            "stop": decimal_text(stop),
            "symbol": symbol,
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return Signal(symbol=symbol, side=side, entry=entry, stop=stop, normalized_json=normalized)
