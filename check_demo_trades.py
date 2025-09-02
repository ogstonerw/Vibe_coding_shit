#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Быстрый просмотр демо-сделок
"""

import json
import os

def check_demo_trades():
    """Проверяет демо-сделки"""
    print("🔍 ПРОВЕРКА ДЕМО-СДЕЛОК")
    print("=" * 50)
    
    # Проверяем файл с сигналами
    if os.path.exists('signals_history.json'):
        with open('signals_history.json', 'r', encoding='utf-8') as file:
            signals = json.load(file)
        print(f"📊 Найдено сигналов: {len(signals)}")
        
        if signals:
            print(f"📋 Последние сигналы:")
            for i, signal in enumerate(signals[-3:], 1):
                print(f"   {i}. {signal['position_type']} - {signal['channel_name']}")
                print(f"      Вход: {signal.get('entry_price', 'Нет')}")
                print(f"      Стоп: {signal.get('stop_loss', 'Нет')}")
                print(f"      Время: {signal.get('timestamp', 'Нет')}")
                print()
    else:
        print("❌ Файл signals_history.json не найден")
    
    # Проверяем файл с демо-сделками
    if os.path.exists('demo_trades.json'):
        with open('demo_trades.json', 'r', encoding='utf-8') as file:
            demo_trades = json.load(file)
        print(f"💼 Найдено демо-сделок: {len(demo_trades)}")
        
        if demo_trades:
            print(f"📈 Открытые сделки:")
            open_trades = [t for t in demo_trades if t['status'] == 'OPEN']
            for i, trade in enumerate(open_trades, 1):
                print(f"   {i}. {trade['side']} {trade['symbol']}")
                print(f"      ID: {trade['trade_id']}")
                print(f"      Вход: {trade['entry_price']}")
                print(f"      Текущая цена: {trade['current_price']}")
                print(f"      P&L: {trade['pnl']} USDT ({trade['pnl_percent']}%)")
                print()
            
            if not open_trades:
                print("   Нет открытых сделок")
    else:
        print("❌ Файл demo_trades.json не найден")
    
    print("💡 Для запуска бота: python main_improved.py")
    print("💡 Для детального мониторинга: python demo_trade_monitor.py")

if __name__ == "__main__":
    check_demo_trades()
