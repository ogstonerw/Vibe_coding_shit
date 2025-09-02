#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import logging
from bitget_integration import BitgetTrader
from market.watcher import Watcher

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

async def test_simple_integration():
    """Упрощенный тест интеграции"""
    print("🧪 Упрощенное тестирование системы...")
    
    # 1. Создаем Bitget трейдер
    trader = BitgetTrader()
    print("✅ Bitget трейдер создан")
    
    # 2. Создаем Watcher
    watcher = Watcher(
        get_now_price=test_get_price,
        on_breakeven=test_on_breakeven,
        poll_interval_sec=1
    )
    print("✅ Watcher создан")
    
    # 3. Тестовый план (имитируем результат Executor)
    plan_dict = {
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'entry': 30000.0,
        'stop': 29500.0,
        'tps': [30500.0, 31000.0, 31500.0],
        'tp_shares': [0.5, 0.3, 0.2],
        'breakeven_after_tp': 2,
        'qty_total': 0.1
    }
    
    print("\n📊 Тестовый план:")
    print(f"   Символ: {plan_dict['symbol']}")
    print(f"   Сторона: {plan_dict['side']}")
    print(f"   Вход: {plan_dict['entry']}")
    print(f"   Стоп: {plan_dict['stop']}")
    print(f"   Тейки: {plan_dict['tps']}")
    print(f"   Доли TP: {plan_dict['tp_shares']}")
    
    # 4. Регистрируем план в Watcher
    print("\n🔄 Регистрация плана в Watcher...")
    watcher.register_plan(plan_dict)
    print(f"✅ План зарегистрирован: {plan_dict.get('plan_id')}")
    
    # 5. Запускаем Watcher
    print("\n🔄 Запуск Watcher на 60 секунд...")
    print("   Ожидаем: TP1 @ 30500, TP2 @ 31000, затем безубыток")
    
    task = asyncio.create_task(watcher.start())
    
    # Ждем 60 секунд
    await asyncio.sleep(60)
    
    # Останавливаем watcher
    watcher.stop()
    await task
    
    print("\n✅ Упрощенный тест завершен!")

if __name__ == "__main__":
    asyncio.run(test_simple_integration())
