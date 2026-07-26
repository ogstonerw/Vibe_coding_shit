from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any


class Source(StrEnum):
    SCALPING = "scalping"
    INTRADAY = "intraday"


class Side(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass(frozen=True, slots=True)
class RawMessage:
    source: Source
    channel_id: str
    message_id: int
    revision: int
    timestamp: str
    text: str
    payload_hash: str

    @property
    def channel_key(self) -> str:
        return hashlib.sha256(self.channel_id.encode("utf-8")).hexdigest()

    @property
    def db_identity(self) -> tuple[str, str, str, str]:
        """Pseudonymous SQLite identity with bounded integers represented exactly."""

        return (
            self.source.value,
            self.channel_key,
            str(self.message_id),
            str(self.revision),
        )

    @property
    def identity_text(self) -> str:
        material = "|".join(self.db_identity).encode("utf-8")
        return "event_" + hashlib.sha256(material).hexdigest()


@dataclass(frozen=True, slots=True)
class Signal:
    symbol: str
    side: Side
    entry: Decimal
    stop: Decimal
    normalized_json: str


@dataclass(frozen=True, slots=True)
class SizingResult:
    allocation: Decimal
    bucket: Decimal
    risk_budget: Decimal
    unit_loss: Decimal
    quantity: Decimal
    risk_amount: Decimal
    notional: Decimal


@dataclass(frozen=True, slots=True)
class SimulatedLimitIntent:
    intent_id: str
    setup_id: str
    symbol: str
    side: Side
    entry: Decimal
    stop: Decimal
    quantity: Decimal
    risk_budget: Decimal
    risk_amount: Decimal
    notional: Decimal


@dataclass(frozen=True, slots=True)
class Outcome:
    disposition: str
    reason: str
    journaled: bool
    event_identity: str | None = None
    original_disposition: str | None = None
    original_reason: str | None = None
    setup_id: str | None = None
    intent_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "disposition": self.disposition,
            "journaled": self.journaled,
            "reason": self.reason,
        }
        optional = {
            "event_identity": self.event_identity,
            "intent_id": self.intent_id,
            "original_disposition": self.original_disposition,
            "original_reason": self.original_reason,
            "setup_id": self.setup_id,
        }
        result.update({key: value for key, value in optional.items() if value is not None})
        return result


def decimal_text(value: Decimal) -> str:
    """Return a deterministic non-exponent representation."""

    if value.is_zero():
        return "0"
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered
