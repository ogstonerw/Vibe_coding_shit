from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class LegPlan:
    qty: float           # Кол-во (в "коинах", для линейного USDT-перпа это ~контракт/коин qty)
    notional: float      # Номинал = qty * entry
    margin: float        # Требуемая маржа = notional / L
    entry: float
    stop: float
    leverage: int

def _delta_sl(entry: float, stop: float) -> float:
    d = abs(entry - stop)
    if d <= 0:
        raise ValueError("Некорректное расстояние до стопа")
    return d

def risk_usdt(equity_sub: float, pct: float) -> float:
    return equity_sub * (pct / 100.0)

def qty_for_risk(entry: float, stop: float, risk_usd: float) -> float:
    """
    Для линейных USDT-перпетуалов P/L ≈ (price_out - price_in) * qty
    => qty = risk_usd / ΔSL
    """
    return risk_usd / _delta_sl(entry, stop)

def build_leg(entry: float, stop: float, equity_sub: float, leg_risk_pct: float, leverage: int) -> LegPlan:
    r = risk_usdt(equity_sub, leg_risk_pct)
    qty = qty_for_risk(entry, stop, r)
    notional = qty * entry
    margin = notional / max(leverage, 1)
    return LegPlan(qty=qty, notional=notional, margin=margin, entry=entry, stop=stop, leverage=leverage)

def scale_leg_to_margin(leg: LegPlan, max_margin: float) -> LegPlan:
    if leg.margin <= max_margin:
        return leg
    k = max_margin / leg.margin
    return LegPlan(
        qty=leg.qty * k,
        notional=leg.notional * k,
        margin=leg.margin * k,
        entry=leg.entry,
        stop=leg.stop,
        leverage=leg.leverage
    )

def tp_shares_cover_total_risk(entry: float, tp1: float, tp2: float, total_risk_usd: float, qty_total: float) -> Tuple[float, float]:
    """
    Подбираем равные доли f на TP1 и TP2, чтобы суммарная прибыль >= total_risk_usd:
      profit = f*qty*(|E-TP1| + |E-TP2|)
      f >= total_risk_usd / (qty*(Δ1+Δ2))
    Ограничиваем f ≤ 0.5 (на два тейка максимум 100% позиции).
    """
    d1 = abs(entry - tp1)
    d2 = abs(entry - tp2)
    denom = max(qty_total * (d1 + d2), 1e-9)
    f = min(max(total_risk_usd / denom, 0.0), 0.5)
    return f, f

def split_rest_even(rest_share: float, rest_count: int) -> List[float]:
    if rest_count <= 0 or rest_share <= 0:
        return []
    each = round(rest_share / rest_count, 6)
    return [each] * rest_count
