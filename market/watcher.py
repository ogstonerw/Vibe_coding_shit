# market/watcher.py
import asyncio
import time
from typing import Callable, Dict, List, Optional
import httpx
import logging

logger = logging.getLogger(__name__)

class Watcher:
    def __init__(self, get_now_price: Callable[[], float], on_breakeven: Callable[[Dict], None], poll_interval_sec: int = 3):
        self.get_now_price = get_now_price         # функция, которая возвращает текущую цену BTCUSDT
        self.on_breakeven = on_breakeven           # коллбек при срабатывании условия БУ
        self.poll_interval_sec = poll_interval_sec
        self._plans: List[Dict] = []               # список активных планов
        self._tp_hit_count: Dict[str, int] = {}    # plan_id -> сколько TP достигнуто
        self._stopped = False

    def register_plan(self, plan: Dict):
        """Добавь уникальный plan_id, например f"{symbol}:{side}:{entry}:{stop}:{time.time_ns()}" """
        plan_id = plan.get("plan_id")
        if not plan_id:
            plan_id = f"{plan['symbol']}:{plan['side']}:{plan['entry']}:{plan['stop']}:{int(time.time()*1000)}"
            plan["plan_id"] = plan_id
        self._plans.append(plan)
        self._tp_hit_count[plan_id] = 0
        logger.info(f"[Watcher] Зарегистрирован план {plan_id}")

    async def start(self):
        self._stopped = False
        logger.info("[Watcher] Запуск наблюдателя цен")
        while not self._stopped:
            try:
                price = self.get_now_price()
                await self._tick(price)
            except Exception as e:
                logger.error(f"[Watcher] error: {e}")
            await asyncio.sleep(self.poll_interval_sec)

    async def _tick(self, price: float):
        # для каждого плана проверяем TP-порог(и)
        remain_plans: List[Dict] = []
        for plan in self._plans:
            pid = plan["plan_id"]
            tps = plan.get("tps", [])
            count_needed = int(plan.get("breakeven_after_tp", 2))
            side = plan["side"]
            # считаем, сколько TP «пересечено» текущей ценой
            hit = self._tp_hit_count.get(pid, 0)

            # Для LONG: TP считается достигнутым, когда price >= TP
            # Для SHORT: TP считается достигнутым, когда price <= TP
            new_hit = hit
            for i in range(hit, len(tps)):
                tp = tps[i]
                if side == "LONG" and price >= tp: 
                    new_hit += 1
                elif side == "SHORT" and price <= tp:
                    new_hit += 1
                else:
                    break  # дальше TP ещё дальше от цены

            if new_hit != hit:
                self._tp_hit_count[pid] = new_hit
                logger.info(f"[Watcher] plan {pid} TP hit count: {new_hit}/{len(tps)} (price={price})")

            if new_hit >= count_needed:
                # переносим в БУ один раз
                try:
                    self.on_breakeven(plan)
                except Exception as e:
                    logger.error(f"[Watcher] on_breakeven error: {e}")
                # этот план можно удалить
                continue

            remain_plans.append(plan)

        self._plans = remain_plans

    def stop(self):
        self._stopped = True
        logger.info("[Watcher] Остановка наблюдателя цен")

# Утилита: получение цены с Bitget (можно не использовать в тестах)
async def fetch_bitget_last_price() -> Optional[float]:
    try:
        # [Неподтверждено] проверь символ и путь под твой рынок (umcbl)
        url = "https://api.bitget.com/api/mix/v1/market/ticker?symbol=BTCUSDT_UMCBL"
        async with httpx.AsyncClient(timeout=5.0) as http:
            r = await http.get(url)
            if r.status_code == 200:
                data = r.json()
                # ожидаем data["data"]["last"] или похожее поле — проверь и поправь
                # [Неподтверждено] ниже — пример рабочего варианта
                last = float(data["data"]["last"])
                return last
    except Exception as e:
        logger.error(f"[Watcher] fetch price error: {e}")
    return None
