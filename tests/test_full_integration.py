#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import logging
from bitget_integration import BitgetTrader
from market.watcher import Watcher
from trader.executor import Executor

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_get_price():
    """Синтетическая цена для тестирования"""
    if not hasattr(test_get_price, 'price'):
        test_get_price.price = 30000.0
    test_get_price.price += 50.0
    return test_get_price.price

def test_on_breakeven(plan):
    """Callback для безубытка"""
    print(f"🎯 Сработал безубыток для плана {plan.get('plan_id')}")
    print(f"   Символ: {plan.get('symbol')}")
    print(f"   Сторона: {plan.get('side')}")
    print(f"   Вход: {plan.get('entry')}")
    print(f"   Стоп: {plan.get('stop')}")
    
    # Имитируем вызов Bitget API
    print("🔁 Перенос SL → БУ...")
    print("✅ SL перенесен в БУ")

async def test_full_integration():
    """Полный тест интеграции"""
    print("🧪 Комплексное тестирование системы...")
    
    # 1. Создаем Bitget трейдер
    trader = BitgetTrader()
    print("✅ Bitget трейдер создан")
    
    # 2. Создаем Executor
    executor = Executor(trader, dry_run=True)
    print("✅ Executor создан")
    
    # 3. Создаем Watcher
    watcher = Watcher(
        get_now_price=test_get_price,
        on_breakeven=test_on_breakeven,
        poll_interval_sec=1
    )
    print("✅ Watcher создан")
    
    # 4. Тестовый сигнал
    class TestSignal:
        def __init__(self):
            self.position_type = "LONG"
            self.entry_price = 30000.0
            self.entry_zone = [29950.0, 30050.0]
            self.stop_loss = 29500.0
            self.take_profits = [30500.0, 31000.0, 31500.0]
            self.raw_text = "LONG BTCUSDT @ 30000 SL 29500 TP1 30500 TP2 31000 TP3 31500"
    
    signal = TestSignal()
    
    # 5. Контекст
    context = {
        "source": "INTRADAY",
        "equity_sub": 850.0,
        "risk_total_pct": 3.0,
        "risk_leg_pct": 1.5,
        "leverage_min": 10,
        "breakeven_after_tp": 2
    }
    
    print("\n📊 Тестовый сигнал:")
    print(f"   Сторона: {signal.position_type}")
    print(f"   Вход: {signal.entry_zone}")
    print(f"   Стоп: {signal.stop_loss}")
    print(f"   Тейки: {signal.take_profits}")
    
    # 6. Создаем план через Executor
    print("\n🔄 Создание плана через Executor...")
    plan = executor.plan_from_signal(signal, context)
    print(f"✅ План создан: {plan.symbol} {plan.side} @ {plan.entry_price}")
    
    # 7. Размещаем ордера
    print("\n🔄 Размещение ордеров...")
    orders, plan_dict = executor.place_all(plan)
    print(f"✅ Размещено {len(orders)} ордеров")
    
    # 8. Регистрируем план в Watcher
    print("\n🔄 Регистрация плана в Watcher...")
    watcher.register_plan(plan_dict)
    print(f"✅ План зарегистрирован: {plan_dict.get('plan_id')}")
    
    # 9. Запускаем Watcher
    print("\n🔄 Запуск Watcher на 60 секунд...")
    print("   Ожидаем: TP1 @ 30500, TP2 @ 31000, затем безубыток")
    
    task = asyncio.create_task(watcher.start())
    
    # Ждем 60 секунд
    await asyncio.sleep(60)
    
    # Останавливаем Watcher
    watcher.stop()
    await task
    
    print("\n✅ Комплексный тест завершен!")

if __name__ == "__main__":
    asyncio.run(test_full_integration())
