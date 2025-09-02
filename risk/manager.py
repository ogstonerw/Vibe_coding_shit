# risk/manager.py
from dataclasses import dataclass, field
from typing import List, Optional, Literal, Dict
from config.settings import settings
from risk.formulas import (
    PositionLeg, leg_sizing, risk_usdt, tp_shares_cover_risk
)

Side = Literal["BUY", "SELL"]

@dataclass
class OrderPlan:
    side: Side
    symbol: str
    entry_type: Literal["limit_zone", "market"]
    entry_price: Optional[float]           # mid зоны или None для market
    entry_zone: Optional[List[float]]      # [low, high]
    leg1: PositionLeg
    leg2: Optional[PositionLeg]            # при (1/2); может быть None, если не доливаем
    tp_levels: List[float]
    tp_shares: List[float]                 # доли на каждый TP (сумма <= 1.0)
    sl_price: float
    move_sl_to_be_after_tp: int            # после какого TP переносим в БУ (обычно 2)
    meta: Dict = field(default_factory=dict)

def choose_entry_price_from_zone(zone: List[float]) -> float:
    low, high = sorted(zone)[:2]
    return round((low + high) / 2, 2)

def build_order_plan(
    source: str,                    # "SCALPING" | "INTRADAY"
    side: Side,
    entry_zone: List[float],        # [low, high]
    stop_loss: float,
    tp_levels: List[float],         # список уровней
    legs: str = "1/2",              # "1/2" или "1/3" и т.п. — сейчас используем "1/2"
    leverage_hint: Optional[int] = None
) -> OrderPlan:
    # Backwards-compatible: original code expected flat attributes on settings
    # New config.settings exposes grouped dataclasses (bitget, risk, behavior).
    # Map the required values here.
    symbol = getattr(settings, 'SYMBOL', None) or getattr(settings, 'bitget', None) and settings.bitget.symbol
    assert symbol == "BTCUSDT", "Сейчас торгуем только BTCUSDT по ТЗ"

    # Поддепозит по источнику
    equity_total = getattr(settings, 'EQUITY_USDT', None) or settings.risk.equity_usdt
    if source.upper() == "SCALPING":
        equity_sub = equity_total * settings.risk.split_scalping_pct / 100.0
    else:
        equity_sub = equity_total * settings.risk.split_intraday_pct / 100.0

    # Риски
    risk_total_usdt = risk_usdt(equity_sub, settings.risk.risk_total_cap_pct)  # 3% от поддепозита
    risk_leg_pct = settings.risk.risk_leg_pct                                  # 1.5% на «ногу» при 1/2

    # Плечо
    L = leverage_hint or settings.risk.leverage_min

    # Выбираем вход (середина зоны)
    entry_price = choose_entry_price_from_zone(entry_zone)

    # Размер первой ноги
    leg1 = leg_sizing(entry_price, stop_loss, equity_sub, risk_leg_pct, L)

    # Вторая нога (если 1/2) — симметричная по риску, но ты можешь открыть её позже по событию
    leg2 = None
    if legs.strip() == "1/2":
        leg2 = leg_sizing(entry_price, stop_loss, equity_sub, risk_leg_pct, L)

    # Доли на TP: хотим покрыть risk_total_usdt двумя первыми тейками (если они есть)
    tp_shares = []
    if len(tp_levels) >= 2:
        f1, f2 = tp_shares_cover_risk(
            entry=entry_price,
            stop=stop_loss,
            tp1=tp_levels[0],
            tp2=tp_levels[1],
            total_risk_usdt=risk_total_usdt,
            qty_total=(leg1.qty + (leg2.qty if leg2 else 0.0))
        )
        tp_shares = [f1, f2]
        # Остальные тейки равномерно на остаток
        rest = max(0.0, 1.0 - (f1 + f2))
        if len(tp_levels) > 2 and rest > 0:
            each = round(rest / (len(tp_levels) - 2), 4)
            tp_shares.extend([each] * (len(tp_levels) - 2))
    else:
        # Если TP < 2 — кладём всё на первый TP
        tp_shares = [1.0] + [0.0] * max(0, len(tp_levels) - 1)

    return OrderPlan(
        side=side,
    symbol=symbol,
        entry_type="limit_zone",
        entry_price=entry_price,
        entry_zone=entry_zone,
        leg1=leg1,
        leg2=leg2,
        tp_levels=tp_levels[:10],
        tp_shares=tp_shares[:10],
        sl_price=stop_loss,
    move_sl_to_be_after_tp=settings.risk.breakeven_after_tp,
        meta={
            "source": source,
            "equity_sub": equity_sub,
            "risk_total_usdt": risk_total_usdt,
            "note": "После TP2 перенос в БУ"
        }
    )
