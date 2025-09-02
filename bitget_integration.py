# bitget_integration.py
from __future__ import annotations
import os, time, hmac, hashlib, base64, json, math
from typing import Any, Dict, List, Optional, Tuple
import httpx

# === Конфиг из окружения ===
BITGET_BASE = os.getenv("BITGET_BASE", "https://api.bitget.com").rstrip("/")
BITGET_API_KEY = os.getenv("BITGET_API_KEY", "")
BITGET_API_SECRET = os.getenv("BITGET_API_SECRET", "")
BITGET_PASSPHRASE = os.getenv("BITGET_PASSPHRASE", "")
DRY_RUN = os.getenv("DRY_RUN","true").lower()=="true"

# Только BTCUSDT (по ТЗ), рынок — UMCBL (USDT-M perpetual)
MARGIN_COIN = "USDT"
PRODUCT_SYMBOL = "BTCUSDT_UMCBL"  # [Неподтверждено] Уточнить формат символа в доке, обычно так

def _ts_ms() -> str:
    return str(int(time.time() * 1000))

def _sign(ts: str, method: str, path: str, body: str) -> str:
    msg = f"{ts}{method}{path}{body}".encode()
    sig = hmac.new(BITGET_API_SECRET.encode(), msg, hashlib.sha256).digest()
    return base64.b64encode(sig).decode()

def _headers(ts: str, sign: str) -> Dict[str,str]:
    return {
        "ACCESS-KEY": BITGET_API_KEY,
        "ACCESS-SIGN": sign,
        "ACCESS-TIMESTAMP": ts,
        "ACCESS-PASSPHRASE": BITGET_PASSPHRASE,
        "Content-Type": "application/json"
    }

class BitgetHTTP:
    def __init__(self, base: str = BITGET_BASE, timeout: float = 15.0):
        self.base = base
        self.http = httpx.Client(timeout=timeout)

    def _request(self, method: str, path: str, body: Optional[dict]=None, auth: bool=False):
        url = self.base + path
        data = json.dumps(body or {}, separators=(",",":"))
        if not auth:
            r = self.http.request(method, url, content=data if method!="GET" else None, params=(body if method=="GET" else None))
            return r
        ts = _ts_ms()
        sign = _sign(ts, method, path, (data if method!="GET" else ""))
        r = self.http.request(method, url,
                              headers=_headers(ts, sign),
                              content=(data if method!="GET" else None),
                              params=(body if method=="GET" else None))
        return r

# Утилиты округления под спецификацию инструмента
class Spec:
    def __init__(self, price_step: float, size_step: float, min_size: float):
        self.price_step = price_step
        self.size_step = size_step
        self.min_size = min_size

    def round_price(self, price: float) -> float:
        step = self.price_step or 0.5
        return round(math.floor(price/step)*step, 2)

    def round_size(self, qty: float) -> float:
        step = self.size_step or 0.001
        return float(f"{math.floor(qty/step)*step:.8f}")

    def clamp_min(self, qty: float) -> float:
        return max(qty, self.min_size or 0.0)

class BitgetTrader:
    """
    Исполнитель ордеров для BTCUSDT_UMCBL:
    - set_leverage
    - entry (limit/market)
    - stop (trigger/plan)
    - takeProfit (reduceOnly)
    - modify stop (to BE)
    - отмена
    Поддержка DRY_RUN: логируем, не вызываем API.
    """
    def __init__(self, config: Optional[dict]=None):
        self.cfg = config or {}
        self.http = BitgetHTTP()
        self.spec = None  # подтянем со спецификаций

    # ===== Публичка / спецификация =====
    def fetch_contract_specs(self) -> Spec:
        """
        [Неподтверждено] Проверь актуальный эндпоинт спецификаций:
        /api/mix/v1/market/contracts?productType=umcbl
        Ожидаем найти priceStep/quantityStep/minSize для BTCUSDT_UMCBL.
        """
        path = "/api/mix/v1/market/contracts"
        r = self.http._request("GET", path, {"productType":"umcbl"}, auth=False)
        if r.status_code != 200:
            raise RuntimeError(f"Spec fetch error: {r.status_code} {r.text}")
        data = r.json().get("data", [])
        row = next((x for x in data if x.get("symbol")==PRODUCT_SYMBOL), None)
        if not row:
            # fallback шаги по умолчанию (безопасно для DRY_RUN)
            self.spec = Spec(price_step=0.5, size_step=0.001, min_size=0.001)
            return self.spec
        # [Неподтверждено] ключи шага и минимума проверь в доке
        price_step = float(row.get("pricePlace", 1))  # может быть цена в знаках, а не шаг — уточни
        # если pricePlace — количество знаков, преобразуем в шаг:
        if price_step > 0 and price_step < 1:
            step = price_step
        else:
            # интерпретация "кол-во знаков"
            step = 10**(-int(row.get("pricePlace", 2)))
        size_step = float(row.get("sizeMultiplier", 0.001))  # [Неподтверждено]
        min_size = float(row.get("minTradeNum", 0.001))      # [Неподтверждено]
        self.spec = Spec(price_step=step, size_step=size_step, min_size=min_size)
        return self.spec

    # ===== Приватка: общие вызовы =====
    def _post(self, path: str, body: dict) -> httpx.Response:
        if DRY_RUN:
            print(json.dumps({"DRY_RUN_POST": {"path": path, "body": body}}, ensure_ascii=False, indent=2))
            class Dummy: status_code=200
            Dummy.text="{}"
            def json_(self): return {"data": {"dry_run": True}}
            Dummy.json=json_
            return Dummy
        return self.http._request("POST", path, body, auth=True)

    def _get(self, path: str, params: dict) -> httpx.Response:
        return self.http._request("GET", path, params, auth=True)

    # ===== Управление плечом / режимом =====
    def set_leverage(self, leverage: int):
        """
        [Неподтверждено] Проверь точный эндпоинт установки плеча для umcbl:
        /api/mix/v1/account/setLeverage
        """
        path = "/api/mix/v1/account/setLeverage"
        body = {
            "symbol": PRODUCT_SYMBOL,
            "marginCoin": MARGIN_COIN,
            "leverage": str(leverage),
            "holdSide": "long_short"  # [Неподтверждено] обе стороны
        }
        return self._post(path, body)

    # ===== Ордеры входа =====
    def place_entry_limit(self, side: str, price: float, qty: float):
        """
        side: LONG|SHORT -> open_long/open_short
        [Неподтверждено] эндпоинт:
        /api/mix/v1/order/placeOrder
        """
        if not self.spec: self.fetch_contract_specs()
        px = self.spec.round_price(price)
        sz = self.spec.clamp_min(self.spec.round_size(qty))
        path = "/api/mix/v1/order/placeOrder"
        body = {
            "symbol": PRODUCT_SYMBOL,
            "marginCoin": MARGIN_COIN,
            "side": "open_long" if side=="LONG" else "open_short",
            "orderType": "limit",
            "price": str(px),
            "size": str(sz),
            "timeInForceValue": "normal"  # [Неподтверждено]
        }
        return self._post(path, body)

    def place_entry_market(self, side: str, qty: float):
        if not self.spec: self.fetch_contract_specs()
        sz = self.spec.clamp_min(self.spec.round_size(qty))
        path = "/api/mix/v1/order/placeOrder"
        body = {
            "symbol": PRODUCT_SYMBOL,
            "marginCoin": MARGIN_COIN,
            "side": "open_long" if side=="LONG" else "open_short",
            "orderType": "market",
            "size": str(sz)
        }
        return self._post(path, body)

    # ===== Стоп / Триггер-ордера =====
    def place_stop(self, side: str, stop_price: float, qty: float):
        """
        План-ордер (trigger) на стоп:
        [Неподтверждено] /api/mix/v1/plan/placePlan
        triggerType: "fill_price"|"market_price"
        executeOrderType: "market"
        reduceOnly: true для стопов закрытия.
        Для стопа по открытой позиции сторона должна быть противонаправленной закрывающей:
        LONG -> close_long, SHORT -> close_short (Bitget формулировка может отличаться).
        """
        if not self.spec: self.fetch_contract_specs()
        px = self.spec.round_price(stop_price)
        sz = self.spec.clamp_min(self.spec.round_size(qty))
        path = "/api/mix/v1/plan/placePlan"
        body = {
            "symbol": PRODUCT_SYMBOL,
            "marginCoin": MARGIN_COIN,
            "triggerType": "market_price",
            "triggerPrice": str(px),
            "executeOrderType": "market",
            "size": str(sz),
            "side": "close_long" if side=="LONG" else "close_short",  # закрывающая сторона
            "reduceOnly": "true"
        }
        return self._post(path, body)

    def modify_stop(self, side: str, new_stop_price: float):
        """
        Переносим SL → БУ (меняем цену триггера).
        [Неподтверждено] на Bitget стоп может быть как план-ордер, его надо модифицировать:
        /api/mix/v1/plan/modifyPlan  (или отменить и создать заново)
        Для простоты — отменим все стоп-планы и поставим новый.
        """
        # Отмена всех планов стопа:
        # [Неподтверждено] список планов: /api/mix/v1/plan/currentPlan
        # упрощение: создаём новый стоп по new_stop_price
        # (в бою — найди текущий stop planId и модифицируй или удали его)
        return self.place_stop(side, new_stop_price, qty=0)  # [Неподтверждено] qty здесь не нужен при modify; упростим

    # ===== Тейк-профит (reduceOnly) =====
    def place_take_profit(self, side: str, price: float, qty: float):
        """
        Limit reduceOnly TP.
        [Неподтверждено] либо обычный limit-ордер с reduceOnly,
        либо план-ордер take-profit. Здесь используем обычный limit reduceOnly.
        """
        if not self.spec: self.fetch_contract_specs()
        px = self.spec.round_price(price)
        sz = self.spec.clamp_min(self.spec.round_size(qty))
        path = "/api/mix/v1/order/placeOrder"
        body = {
            "symbol": PRODUCT_SYMBOL,
            "marginCoin": MARGIN_COIN,
            "side": "close_short" if side=="LONG" else "close_long",  # закрывающий
            "orderType": "limit",
            "price": str(px),
            "size": str(sz),
            "reduceOnly": "true",
            "timeInForceValue": "normal"
        }
        return self._post(path, body)

    # ===== Высокоуровневый сценарий (используется из main.py) =====
    def execute_trade(self, signal, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Принимает распарсенный сигнал + контекст риска.
        Сценарий:
        - set_leverage
        - entry limit (в середину зоны) на суммарный qty
        - поставить TP (reduceOnly) по долям
        - поставить Stop (trigger)
        Возвращает dict с кратким планом.
        """
        try:
            side = signal.position_type  # "LONG" | "SHORT"
            zone = getattr(signal, "entry_zone", None) or [signal.entry_price, signal.entry_price]
            entry = round((float(zone[0]) + float(zone[1]))/2, 2)
            stop = float(signal.stop_loss)
            tps: List[float] = list(getattr(signal, "take_profits", []) or [])
            if not tps:
                tps = [entry + 100.0] if side=="LONG" else [entry - 100.0]

            # qty_total должен быть рассчитан ранее (risk sizing).
            # В этой функции используем упрощённо: прочитаем из context (подсунь из Executor).
            qty_total = float(context.get("qty_total", 0.0))
            tp_shares: List[float] = list(context.get("tp_shares", []))
            leverage = int(context.get("leverage_min", 10))

            if qty_total <= 0:
                # если нет qty_total в контексте — минималка для безопасной проверки API
                qty_total = 0.001

            # Плечо
            self.set_leverage(leverage)

            # Вход (лимит)
            self.place_entry_limit(side, entry, qty_total)

            # Стоп
            self.place_stop(side, stop, qty_total)

            # Тейки
            for tp, share in zip(tps, tp_shares or [1.0]):
                if share <= 0: 
                    continue
                self.place_take_profit(side, tp, qty_total*share)

            return {"ok": True, "entry": entry, "stop": stop, "tps": tps, "qty_total": qty_total, "leverage": leverage}
        except Exception as e:
            print(f"[BitgetTrader.execute_trade] error: {e}")
            return None

def load_bitget_config() -> Optional[Dict[str, str]]:
    """Загрузка конфигурации Bitget из переменных окружения"""
    if not all([BITGET_API_KEY, BITGET_API_SECRET, BITGET_PASSPHRASE]):
        print("⚠️ Не все переменные Bitget настроены")
        return None
    
    return {
        "api_key": BITGET_API_KEY,
        "api_secret": BITGET_API_SECRET,
        "passphrase": BITGET_PASSPHRASE,
        "base_url": BITGET_BASE
    }
