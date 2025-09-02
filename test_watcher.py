#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import time
from market.watcher import Watcher

def test_get_price():
    """Тестовая функция для получения цены"""
    # Синтетическая цена, которая растет
    if not hasattr(test_get_price, 'price'):
        test_get_price.price = 30000.0
    test_get_price.price += 50.0
    return test_get_price.price

def test_on_breakeven(plan):
    """Тестовый callback для безубытка"""
    print(f"🎯 Сработал безубыток для плана {plan.get('plan_id')}")
    print(f"   Символ: {plan.get('symbol')}")
    print(f"   Сторона: {plan.get('side')}")
    print(f"   Вход: {plan.get('entry')}")
    print(f"   Стоп: {plan.get('stop')}")

async def main():
    print("🧪 Тестирование Watcher...")
    
    # Создаем watcher
    watcher = Watcher(
        get_now_price=test_get_price,
        on_breakeven=test_on_breakeven,
        poll_interval_sec=2
    )
    
    # Создаем тестовый план
    test_plan = {
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'entry': 30000.0,
        'stop': 29500.0,
        'tps': [30500.0, 31000.0, 31500.0],  # TP1, TP2, TP3
        'tp_shares': [0.5, 0.3, 0.2],
        'breakeven_after_tp': 2  # После 2-го TP переносим в БУ
    }
    
    # Регистрируем план
    watcher.register_plan(test_plan)
    
    print(f"📊 Зарегистрирован план: {test_plan}")
    print("🔄 Запуск watcher на 30 секунд...")
    
    # Запускаем watcher
    task = asyncio.create_task(watcher.start())
    
    # Ждем 30 секунд
    await asyncio.sleep(30)
    
    # Останавливаем watcher
    watcher.stop()
    await task
    
    print("✅ Тест завершен")

if __name__ == "__main__":
    asyncio.run(main())
