#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Улучшенный парсер торговых сигналов
Сгенерирован автоматически на основе обучения на реальных данных
"""

import re
from dataclasses import dataclass
from typing import Optional, List, Dict

@dataclass
class TradingSignal:
    """Структура торгового сигнала"""
    message_id: str
    channel_name: str
    position_type: str  # 'LONG' или 'SHORT'
    entry_price: Optional[str] = None
    stop_loss: Optional[str] = None
    take_profits: List[str] = None
    risk_percent: Optional[str] = None
    leverage: Optional[str] = None
    timestamp: Optional[str] = None
    raw_text: str = ""

class ImprovedSignalParser:
    """Улучшенный парсер торговых сигналов"""
    
    def __init__(self):
        # Ключевые слова для лонгов (расширенный список)
        self.long_keywords = [
            'лонг', 'long', '📈', 'вверх', 'рост', 'покупка', 'buy',
            'лoнг', 'вход в лонг', 'пробую лонг', 'открываю лонг'
        ]
        
        # Ключевые слова для шортов (расширенный список)
        self.short_keywords = [
            'шорт', 'short', '🔴', 'вниз', 'падение', 'продажа', 'sell',
            'шoрт', 'вход в шорт', 'пробую шорт', 'открываю шорт'
        ]
        
        # Ключевые слова шума (уменьшенный список)
        self.noise_keywords = [
            'стрим', 'стримит', 'twitch', 'youtube', 'подписывайтесь',
            'реклама', 'промо', 'конкурс', 'приз', 'анонс'
        ]
        
        # Улучшенные фразы
        self.improved_phrases = [
            'пробую лонг', 'пробую шорт', 'стоп под', 'стоп над',
            'цели:', 'риск:', 'плечо:', 'х5', 'х10', 'х20'
        ]
        
        # Регулярные выражения для извлечения параметров
        self.patterns = {
            'entry': [
                r'пробую\s+(?:лонг|шорт|лoнг|шoрт)\s+(\d{4,6}[-\d{4,6}}]*)',
                r'вход\s+(?:в\s+)?(?:лонг|шорт|лoнг|шoрт)\s+(\d{4,6}[-\d{4,6}}]*)',
                r'(\d{4,6}[-\d{4,6}}]*)\s+(?:лонг|шорт|лoнг|шoрт)',
                r'(?:лонг|шорт|лoнг|шoрт)\s+(\d{4,6}[-\d{4,6}}]*)'
            ],
            'stop': [
                r'стоп\s+(?:под|над)\s+(\d{4,6})',
                r'стоп\s+(\d{4,6})',
                r'сл\s+(\d{4,6})',
                r'стoп\s+(?:под|над)\s+(\d{4,6})'
            ],
            'take_profit': [
                r'цели?:\s*([\d\s\-\n]+)',
                r'тейк\s+(?:профит|цели)\s*([\d\s\-\n]+)',
                r'тп\s*([\d\s\-\n]+)',
                r'цели\s*([\d\s\-\n]+)'
            ],
            'risk': [
                r'риск(?:ом)?\s+(\d+(?:\.\d+)?%)',
                r'(\d+(?:\.\d+)?%)\s+риск',
                r'рискoм\s+(\d+(?:\.\d+)?%)'
            ],
            'leverage': [
                r'плечо:?\s*(х\d+)',
                r'(х\d+)\s+плечо',
                r'леверидж\s*(х\d+)',
                r'плечo:?\s*(х\d+)'
            ]
        }
    
    def is_trading_signal(self, text: str) -> tuple[bool, "Optional[str]"]:
        """Определяет, является ли сообщение торговым сигналом.

        Возвращает кортеж (is_signal, reason). reason — строка с причной отказа
        или None.
        """
        text_lower = text.lower()

        # Проверяем наличие ключевых слов сигналов
        has_signal_keywords = any(
            keyword in text_lower
            for keyword in self.long_keywords + self.short_keywords
        )

        # Проверяем наличие цифр (цен) - более гибко
        has_numbers = bool(re.search(r'\d{3,6}', text))

        # Проверяем длину сообщения
        is_long_enough = len(text.strip()) > 20

        # Проверяем отсутствие явного шума
        has_noise = any(
            keyword in text_lower
            for keyword in self.noise_keywords
        )

        if has_noise:
            return False, "noise"

        if not has_signal_keywords:
            return False, "no keywords"

        if not has_numbers:
            return False, "no numbers"

        if not is_long_enough:
            return False, "too short"

        # Passed basic checks
        return True, None
    
    def extract_position_type(self, text: str) -> Optional[str]:
        """Извлекает тип позиции (LONG/SHORT)"""
        text_lower = text.lower()
        
        if any(keyword in text_lower for keyword in self.long_keywords):
            return 'LONG'
        elif any(keyword in text_lower for keyword in self.short_keywords):
            return 'SHORT'
        
        return None
    
    def extract_parameters(self, text: str) -> Dict[str, str]:
        """Извлекает параметры торгового сигнала"""
        params = {}
        
        for param_type, patterns in self.patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    if param_type == 'take_profit':
                        # Обрабатываем множественные цели
                        tp_text = match.group(1)
                        tp_prices = re.findall(r'\d{4,6}', tp_text)
                        if tp_prices:
                            params[param_type] = '-'.join(tp_prices)
                    else:
                        params[param_type] = match.group(1)
                    break
        
        return params
    
    def parse_signal(self, message_id: str, channel_name: str, text: str, timestamp: str = None) -> Optional[TradingSignal]:
        """Парсит торговый сигнал из текста сообщения"""
        is_sig, reason = self.is_trading_signal(text)
        if not is_sig:
            return None

        position_type = self.extract_position_type(text)
        if not position_type:
            return None
        
        params = self.extract_parameters(text)
        
        # Разбираем take_profits на список
        take_profits = []
        if 'take_profit' in params:
            tp_str = params['take_profit']
            take_profits = re.findall(r'\d{4,6}', tp_str)
        
        return TradingSignal(
            message_id=message_id,
            channel_name=channel_name,
            position_type=position_type,
            entry_price=params.get('entry'),
            stop_loss=params.get('stop'),
            take_profits=take_profits,
            risk_percent=params.get('risk'),
            leverage=params.get('leverage'),
            timestamp=timestamp,
            raw_text=text
        )

# Статистика обучения:
# Всего сообщений: 548
# Сигналов: 142
# Шума: 406
# Найдено паттернов: 1
