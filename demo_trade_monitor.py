#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Мониторинг демо-сделок для торгового бота
Показывает все обработанные сигналы и их статус
"""

import json
import os
from datetime import datetime
from typing import List, Dict
from improved_signal_parser import TradingSignal

class DemoTradeMonitor:
    """Монитор демо-сделок"""
    
    def __init__(self):
        self.signals_file = 'signals_history.json'
        self.demo_trades_file = 'demo_trades.json'
        self.signals = []
        self.demo_trades = []
        
    def load_data(self):
        """Загружает данные о сигналах и демо-сделках"""
        # Загружаем сигналы
        if os.path.exists(self.signals_file):
            with open(self.signals_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
                for item in data:
                    signal = TradingSignal(
                        message_id=item['message_id'],
                        channel_name=item['channel_name'],
                        position_type=item['position_type'],
                        entry_price=item.get('entry_price'),
                        stop_loss=item.get('stop_loss'),
                        take_profits=item.get('take_profits', []),
                        risk_percent=item.get('risk_percent'),
                        leverage=item.get('leverage'),
                        timestamp=item.get('timestamp'),
                        raw_text=item.get('raw_text', '')
                    )
                    self.signals.append(signal)
        
        # Загружаем демо-сделки
        if os.path.exists(self.demo_trades_file):
            with open(self.demo_trades_file, 'r', encoding='utf-8') as file:
                self.demo_trades = json.load(file)
    
    def create_demo_trade(self, signal: TradingSignal) -> Dict:
        """Создает демо-сделку на основе сигнала"""
        # Симулируем текущую цену BTC (можно заменить на реальный API)
        current_price = 45000  # Примерная цена
        
        # Рассчитываем размер позиции
        risk_amount = 0.5  # 0.5% от депозита
        account_balance = 1000  # Предполагаемый баланс
        risk_usdt = account_balance * (risk_amount / 100)
        
        # Рассчитываем размер позиции
        if signal.stop_loss and signal.entry_price:
            entry_price = float(signal.entry_price.split('-')[0])
            stop_price = float(signal.stop_loss)
            price_diff = abs(entry_price - stop_price)
            position_size = (risk_usdt / price_diff) * entry_price
        else:
            position_size = 0.001  # Минимальный размер
        
        demo_trade = {
            'trade_id': f"demo_{signal.message_id}",
            'signal_id': signal.message_id,
            'channel': signal.channel_name,
            'symbol': 'BTCUSDT',
            'side': signal.position_type,
            'entry_price': signal.entry_price,
            'current_price': current_price,
            'stop_loss': signal.stop_loss,
            'take_profit': signal.take_profits[0] if signal.take_profits else None,
            'position_size': round(position_size, 6),
            'leverage': signal.leverage,
            'risk_percent': signal.risk_percent,
            'status': 'OPEN',
            'open_time': signal.timestamp,
            'pnl': 0.0,
            'pnl_percent': 0.0,
            'raw_signal': signal.raw_text[:100] + "..."
        }
        
        return demo_trade
    
    def update_demo_trades(self):
        """Обновляет демо-сделки на основе сигналов"""
        # Создаем демо-сделки для всех сигналов
        for signal in self.signals:
            # Проверяем, есть ли уже демо-сделка для этого сигнала
            existing_trade = next(
                (trade for trade in self.demo_trades if trade['signal_id'] == signal.message_id),
                None
            )
            
            if not existing_trade:
                demo_trade = self.create_demo_trade(signal)
                self.demo_trades.append(demo_trade)
        
        # Сохраняем обновленные демо-сделки
        with open(self.demo_trades_file, 'w', encoding='utf-8') as file:
            json.dump(self.demo_trades, file, ensure_ascii=False, indent=2)
    
    def calculate_pnl(self, trade: Dict) -> tuple:
        """Рассчитывает P&L для сделки"""
        if not trade['entry_price'] or not trade['current_price']:
            return 0.0, 0.0
        
        entry_price = float(trade['entry_price'].split('-')[0])
        current_price = trade['current_price']
        position_size = trade['position_size']
        
        if trade['side'] == 'LONG':
            pnl = (current_price - entry_price) * position_size
        else:  # SHORT
            pnl = (entry_price - current_price) * position_size
        
        pnl_percent = (pnl / (entry_price * position_size)) * 100
        
        return round(pnl, 2), round(pnl_percent, 2)
    
    def show_demo_trades(self):
        """Показывает все демо-сделки"""
        print("📊 ДЕМО-СДЕЛКИ")
        print("=" * 80)
        
        if not self.demo_trades:
            print("❌ Нет демо-сделок")
            return
        
        total_pnl = 0.0
        open_trades = 0
        
        for i, trade in enumerate(self.demo_trades, 1):
            # Обновляем P&L
            pnl, pnl_percent = self.calculate_pnl(trade)
            trade['pnl'] = pnl
            trade['pnl_percent'] = pnl_percent
            
            # Определяем статус
            if trade['stop_loss'] and trade['current_price']:
                stop_price = float(trade['stop_loss'])
                if (trade['side'] == 'LONG' and trade['current_price'] <= stop_price) or \
                   (trade['side'] == 'SHORT' and trade['current_price'] >= stop_price):
                    trade['status'] = 'STOPPED'
            
            if trade['take_profit'] and trade['current_price']:
                tp_price = float(trade['take_profit'])
                if (trade['side'] == 'LONG' and trade['current_price'] >= tp_price) or \
                   (trade['side'] == 'SHORT' and trade['current_price'] <= tp_price):
                    trade['status'] = 'TAKE_PROFIT'
            
            # Выводим информацию о сделке
            status_emoji = {
                'OPEN': '🟢',
                'STOPPED': '🔴',
                'TAKE_PROFIT': '🟡'
            }.get(trade['status'], '⚪')
            
            pnl_emoji = '📈' if pnl >= 0 else '📉'
            
            print(f"\n{i}. {status_emoji} {trade['side']} {trade['symbol']}")
            print(f"   ID: {trade['trade_id']}")
            print(f"   Канал: {trade['channel']}")
            print(f"   Вход: {trade['entry_price']}")
            print(f"   Текущая цена: {trade['current_price']}")
            print(f"   Стоп-лосс: {trade['stop_loss']}")
            print(f"   Тейк-профит: {trade['take_profit']}")
            print(f"   Размер: {trade['position_size']} BTC")
            print(f"   Плечо: {trade['leverage']}")
            print(f"   P&L: {pnl_emoji} {pnl} USDT ({pnl_percent}%)")
            print(f"   Статус: {trade['status']}")
            print(f"   Время открытия: {trade['open_time']}")
            print("-" * 60)
            
            if trade['status'] == 'OPEN':
                open_trades += 1
                total_pnl += pnl
        
        # Общая статистика
        print(f"\n📈 ОБЩАЯ СТАТИСТИКА:")
        print(f"   Всего сделок: {len(self.demo_trades)}")
        print(f"   Открытых сделок: {open_trades}")
        print(f"   Закрытых сделок: {len(self.demo_trades) - open_trades}")
        print(f"   Общий P&L: {'📈' if total_pnl >= 0 else '📉'} {total_pnl} USDT")
        
        # Сохраняем обновленные данные
        with open(self.demo_trades_file, 'w', encoding='utf-8') as file:
            json.dump(self.demo_trades, file, ensure_ascii=False, indent=2)
    
    def show_signals_summary(self):
        """Показывает сводку по сигналам"""
        print(f"\n📋 СВОДКА ПО СИГНАЛАМ:")
        print(f"   Всего сигналов: {len(self.signals)}")
        
        if self.signals:
            long_signals = len([s for s in self.signals if s.position_type == 'LONG'])
            short_signals = len([s for s in self.signals if s.position_type == 'SHORT'])
            
            print(f"   LONG: {long_signals}")
            print(f"   SHORT: {short_signals}")
            
            # Статистика по каналам
            channels = {}
            for signal in self.signals:
                if signal.channel_name not in channels:
                    channels[signal.channel_name] = {'long': 0, 'short': 0}
                
                if signal.position_type == 'LONG':
                    channels[signal.channel_name]['long'] += 1
                else:
                    channels[signal.channel_name]['short'] += 1
            
            print(f"\n📡 По каналам:")
            for channel, stats in channels.items():
                total = stats['long'] + stats['short']
                print(f"   {channel}: {total} сигналов (LONG: {stats['long']}, SHORT: {stats['short']})")
    
    def run_monitor(self):
        """Запускает мониторинг"""
        print("🔍 МОНИТОРИНГ ДЕМО-СДЕЛОК")
        print("=" * 80)
        
        # Загружаем данные
        self.load_data()
        
        # Обновляем демо-сделки
        self.update_demo_trades()
        
        # Показываем сводку по сигналам
        self.show_signals_summary()
        
        # Показываем демо-сделки
        self.show_demo_trades()
        
        print(f"\n💡 Для обновления данных запустите скрипт снова")
        print(f"📁 Данные сохранены в {self.demo_trades_file}")

def main():
    """Основная функция"""
    monitor = DemoTradeMonitor()
    monitor.run_monitor()

if __name__ == "__main__":
    main()
