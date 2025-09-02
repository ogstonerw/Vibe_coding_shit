#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import time
import logging
from market.watcher import Watcher

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_get_price():
    """Тестовая функция для получения цены"""
    # Синтетическая цена, которая растет
    if not hasattr(test_get_price, 'price'):
        test_get_price.price = 30000.0
    test_get_price.price += 50.0
    print(f"💰 Текущая цена: {test_get_price.price}")
    return test_get_price.price

def test_on_breakeven(plan):
    """Тестовый callback для безубытка"""
    print(f"🎯 Сработал безубыток для плана {plan.get('plan_id')}")
    print(f"   Символ: {plan.get('symbol')}")
    print(f"   Сторона: {plan.get('side')}")
    print(f"   Вход: {plan.get('entry')}")
    print(f"   Стоп: {plan.get('stop')}")

async def main():
    print("🧪 Детальное тестирование Watcher...")
    
    # Создаем watcher
    watcher = Watcher(
        get_now_price=test_get_price,
        on_breakeven=test_on_breakeven,
        poll_interval_sec=1  # Проверяем каждую секунду
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
    print("🔄 Запуск watcher на 60 секунд...")
    print("   Ожидаем: TP1 @ 30500, TP2 @ 31000, затем безубыток")
    
    # Запускаем watcher
    task = asyncio.create_task(watcher.start())
    
    # Ждем 60 секунд
    await asyncio.sleep(60)
    
    # Останавливаем watcher
    watcher.stop()
    await task
    
    print("✅ Тест завершен")

if __name__ == "__main__":
    asyncio.run(main())
