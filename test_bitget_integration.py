#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from bitget_integration import BitgetTrader, load_bitget_config

def test_dry_run():
    """Тест DRY_RUN режима"""
    print("🧪 Тестирование Bitget интеграции в DRY_RUN режиме...")
    
    # Создаем трейдер
    trader = BitgetTrader()
    
    # Тестовый сигнал
    class TestSignal:
        def __init__(self):
            self.position_type = "LONG"
            self.entry_price = 30000.0
            self.entry_zone = [29950.0, 30050.0]
            self.stop_loss = 29500.0
            self.take_profits = [30500.0, 31000.0, 31500.0]
    
    signal = TestSignal()
    
    # Контекст
    context = {
        "source": "INTRADAY",
        "equity_sub": 850.0,  # 85% от 1000
        "risk_total_pct": 3.0,
        "risk_leg_pct": 1.5,
        "leverage_min": 10,
        "leverage_max": 20,
        "breakeven_after_tp": 2,
        "qty_total": 0.1,  # тестовый размер
        "tp_shares": [0.5, 0.3, 0.2]
    }
    
    print("📊 Тестовый сигнал:")
    print(f"   Сторона: {signal.position_type}")
    print(f"   Вход: {signal.entry_zone}")
    print(f"   Стоп: {signal.stop_loss}")
    print(f"   Тейки: {signal.take_profits}")
    print(f"   Размер: {context['qty_total']}")
    print(f"   Доли TP: {context['tp_shares']}")
    
    print("\n🔄 Выполнение торговли...")
    result = trader.execute_trade(signal, context)
    
    if result:
        print("✅ Торговля выполнена успешно!")
        print(f"   Результат: {json.dumps(result, indent=2, ensure_ascii=False)}")
    else:
        print("❌ Ошибка выполнения торговли")

def test_real_api():
    """Тест реального API (если настроены ключи)"""
    print("\n🧪 Тестирование реального API...")
    
    config = load_bitget_config()
    if not config:
        print("⚠️ Ключи Bitget не настроены, пропускаем тест реального API")
        return
    
    print("✅ Ключи найдены, тестируем реальное API...")
    
    trader = BitgetTrader(config)
    
    # Тестируем получение спецификаций
    try:
        spec = trader.fetch_contract_specs()
        print(f"✅ Спецификации получены: price_step={spec.price_step}, size_step={spec.size_step}, min_size={spec.min_size}")
    except Exception as e:
        print(f"❌ Ошибка получения спецификаций: {e}")

if __name__ == "__main__":
    # Тест DRY_RUN
    test_dry_run()
    
    # Тест реального API
    test_real_api()
