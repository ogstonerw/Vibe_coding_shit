from __future__ import annotations

import hashlib

from .config import MvpConfig
from .contracts import Outcome, RawMessage, SimulatedLimitIntent, decimal_text
from .journal import Journal
from .parser import EnvelopeError, SignalError, parse_envelope, parse_signal
from .sizing import SizingError, size_first_leg


class OfflineSignalService:
    def __init__(self, config: MvpConfig, journal: Journal) -> None:
        self.config = config
        self.journal = journal

    def process_mapping(self, mapping: object) -> Outcome:
        try:
            event = parse_envelope(mapping)
        except EnvelopeError as exc:
            return Outcome(disposition="rejected", reason=exc.reason, journaled=False)
        return self.process_event(event)

    def _reject(self, event: RawMessage, reason: str) -> Outcome:
        self.journal.insert_event(event, "rejected", reason)
        self.journal.append_journal(event, "DECISION_REJECTED", {"reason": reason})
        return Outcome(
            disposition="rejected",
            reason=reason,
            journaled=True,
            event_identity=event.identity_text,
        )

    def process_event(self, event: RawMessage) -> Outcome:
        with self.journal.transaction():
            existing = self.journal.existing_event(event)
            if existing is not None:
                if existing["payload_hash"] == event.payload_hash:
                    return Outcome(
                        disposition="duplicate",
                        reason="DUPLICATE_EVENT",
                        journaled=False,
                        event_identity=event.identity_text,
                        original_disposition=str(existing["disposition"]),
                        original_reason=str(existing["reason"]),
                    )
                return Outcome(
                    disposition="conflict",
                    reason="EVENT_IDENTITY_CONFLICT",
                    journaled=False,
                    event_identity=event.identity_text,
                )

            if event.channel_id != self.config.channel_for(event.source):
                return self._reject(event, "SOURCE_CHANNEL_NOT_ALLOWED")

            try:
                signal = parse_signal(event.text)
            except SignalError as exc:
                return self._reject(event, exc.reason)

            if self.journal.active_setup_count() >= self.config.max_active_setups:
                return self._reject(event, "MAX_ACTIVE_SETUPS_REACHED")

            try:
                sizing = size_first_leg(signal, event.source, self.config)
            except SizingError as exc:
                return self._reject(event, exc.reason)

            identity_material = (
                f"{self.config.fingerprint}|{event.identity_text}|{signal.normalized_json}"
            ).encode("utf-8")
            setup_id = "setup_" + hashlib.sha256(b"setup|" + identity_material).hexdigest()
            intent_id = "intent_" + hashlib.sha256(b"intent|" + identity_material).hexdigest()
            intent = SimulatedLimitIntent(
                intent_id=intent_id,
                setup_id=setup_id,
                symbol=signal.symbol,
                side=signal.side,
                entry=signal.entry,
                stop=signal.stop,
                quantity=sizing.quantity,
                risk_budget=sizing.risk_budget,
                risk_amount=sizing.risk_amount,
                notional=sizing.notional,
            )

            reason = "ACCEPTED_SIMULATED_LIMIT_INTENT"
            self.journal.insert_event(event, "accepted", reason)
            self.journal.insert_setup(setup_id, event, signal)
            self.journal.insert_intent(intent)
            self.journal.append_journal(
                event,
                "SIMULATED_LIMIT_INTENT_CREATED",
                {
                    "intent_id": intent_id,
                    "quantity": decimal_text(sizing.quantity),
                    "risk_amount": decimal_text(sizing.risk_amount),
                    "setup_id": setup_id,
                },
            )
            return Outcome(
                disposition="accepted",
                reason=reason,
                journaled=True,
                event_identity=event.identity_text,
                setup_id=setup_id,
                intent_id=intent_id,
            )
