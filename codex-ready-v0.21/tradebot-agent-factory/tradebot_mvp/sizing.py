from __future__ import annotations

from decimal import Context, Decimal, ROUND_FLOOR, localcontext

from .config import MvpConfig
from .contracts import Signal, SizingResult, Source


class SizingError(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _is_multiple(value: Decimal, step: Decimal) -> bool:
    return value % step == 0


def size_first_leg(signal: Signal, source: Source, config: MvpConfig) -> SizingResult:
    deterministic_context = Context(
        prec=50,
        rounding=ROUND_FLOOR,
        Emin=-999_999,
        Emax=999_999,
        capitals=1,
        clamp=0,
        flags=[],
        traps=[],
    )
    with localcontext(deterministic_context):
        if not _is_multiple(signal.entry, config.price_tick) or not _is_multiple(
            signal.stop,
            config.price_tick,
        ):
            raise SizingError("PRICE_OFF_TICK")

        allocation = config.allocation_for(source)
        bucket = config.account_equity * allocation
        risk_budget = bucket * config.first_leg_risk
        unit_loss = abs(signal.entry - signal.stop) + config.adverse_cost_per_unit
        if unit_loss <= 0:
            raise SizingError("INVALID_UNIT_LOSS")

        risk_denominator = unit_loss * config.quantity_step
        margin_denominator = signal.entry * config.quantity_step
        risk_steps = (risk_budget / risk_denominator).to_integral_value(rounding=ROUND_FLOOR)
        margin_steps = (
            (bucket * Decimal(config.leverage)) / margin_denominator
        ).to_integral_value(rounding=ROUND_FLOOR)
        step_count = min(risk_steps, margin_steps)
        quantity = step_count * config.quantity_step
        if quantity <= 0:
            raise SizingError("ZERO_QUANTITY")

        risk_amount = quantity * unit_loss
        notional = quantity * signal.entry
        if risk_amount > risk_budget or notional > bucket * Decimal(config.leverage):
            raise SizingError("SIZING_CAP_VIOLATION")

        return SizingResult(
            allocation=allocation,
            bucket=bucket,
            risk_budget=risk_budget,
            unit_loss=unit_loss,
            quantity=quantity,
            risk_amount=risk_amount,
            notional=notional,
        )
