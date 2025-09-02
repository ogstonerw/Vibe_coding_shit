# risk/formulas.py
from dataclasses import dataclass
from typing import Tuple, Optional

@dataclass
class PositionLeg:
    qty: float
    notional: float
    margin: float
    entry_price: float
    stop_price: float
    leverage: int

def delta_sl(entry: float, stop: float) -> float:
    return abs(entry - stop)

def risk_usdt(equity_usdt: float, risk_pct: float) -> float:
    return equity_usdt * (risk_pct / 100.0)

def quantity_for_risk(entry: float, stop: float, risk_usdt_: float) -> float:
    """
    Для линейного USDT-перпетуала: Profit/Loss ≈ (price_out - price_in) * qty
    Значит qty = risk_usdt / ΔSL
    """
    d = delta_sl(entry, stop)
    if d <= 0:
        raise ValueError("Invalid SL distance")
    return risk_usdt_ / d

def leg_sizing(entry: float, stop: float, equity_sub: float, risk_leg_pct: float, leverage: int) -> PositionLeg:
    r_usdt = risk_usdt(equity_sub, risk_leg_pct)
    qty = quantity_for_risk(entry, stop, r_usdt)
    notional = qty * entry
    margin = notional / max(leverage, 1)
    return PositionLeg(qty=qty, notional=notional, margin=margin, entry_price=entry, stop_price=stop, leverage=leverage)

def scale_to_margin(leg: PositionLeg, max_margin: float) -> PositionLeg:
    """
    Если доступной маржи меньше, чем требуется, пропорционально уменьшаем размер.
    """
    if leg.margin <= max_margin:
        return leg
    k = max_margin / leg.margin
    return PositionLeg(
        qty=leg.qty * k,
        notional=leg.notional * k,
        margin=leg.margin * k,
        entry_price=leg.entry_price,
        stop_price=leg.stop_price,
        leverage=leg.leverage
    )

def tp_shares_cover_risk(
    entry: float,
    stop: float,
    tp1: float,
    tp2: float,
    total_risk_usdt: float,
    qty_total: float
) -> Tuple[float, float]:
    """
    Подбираем равные доли f на TP1 и TP2, чтобы суммарная прибыль >= total_risk_usdt.
    P1 = f*qty_total*|entry - tp1|
    P2 = f*qty_total*|entry - tp2|
    Требуем: P1 + P2 >= total_risk_usdt
    => f >= total_risk_usdt / (qty_total*(|entry-tp1| + |entry-tp2|))
    Ограничиваем f ≤ 0.5 (две доли максимум по 50%).
    """
    d1 = abs(entry - tp1)
    d2 = abs(entry - tp2)
    denom = max(qty_total * (d1 + d2), 1e-9)
    f = total_risk_usdt / denom
    f = min(max(f, 0.0), 0.5)
    return (f, f)
