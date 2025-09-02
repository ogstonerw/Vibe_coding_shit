import re
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

@dataclass
class ParsedSignal:
    """Результат парсинга сигнала"""
    direction: str  # BUY | SELL
    symbol: str     # BTCUSDT
    entry_low: float
    entry_high: float
    stop_loss: float
    take_profit: Optional[float] = None
    take_profit2: Optional[float] = None
    risk_percent: Optional[float] = None
    leverage: Optional[int] = None
    confidence: float = 0.0  # 0.0 - 1.0

class SignalParser:
    """Парсер торговых сигналов на основе регулярных выражений"""
    
    def __init__(self):
        # Паттерны для направления
        self.buy_patterns = [
            r'\b(?:buy|long|покупка|лонг|вверх|up|bull)\b',
            r'🟢|✅|📈|🚀|💚',
            r'\+|📊|📈'
        ]
        
        self.sell_patterns = [
            r'\b(?:sell|short|продажа|шорт|вниз|down|bear)\b',
            r'🔴|❌|📉|💥|❤️',
            r'\-|📊|📉'
        ]
        
        # Паттерны для цен
        self.price_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:usdt|usd|\$)?',  # Обычные цены
            r'(\d+(?:\.\d+)?)k',  # Тысячи (например, 45k = 45000)
            r'(\d+(?:\.\d+)?)m',  # Миллионы
        ]
        
        # Паттерны для зон входа
        self.entry_patterns = [
            r'(?:entry|вход|зона|zone)\s*(?:в|at|from|to)?\s*(\d+(?:\.\d+)?)\s*(?:-|to|до)\s*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*(?:-|to|до)\s*(\d+(?:\.\d+)?)\s*(?:entry|вход)',
            r'buy\s*(?:at|в|from)\s*(\d+(?:\.\d+)?)\s*(?:-|to|до)\s*(\d+(?:\.\d+)?)',
            r'sell\s*(?:at|в|from)\s*(\d+(?:\.\d+)?)\s*(?:-|to|до)\s*(\d+(?:\.\d+)?)',
        ]
        
        # Паттерны для стоп-лосса
        self.sl_patterns = [
            r'(?:sl|stop|стоп|stop\s*loss)\s*(?:at|в|:)?\s*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*(?:sl|stop|стоп)',
            r'stop\s*loss\s*(\d+(?:\.\d+)?)',
        ]
        
        # Паттерны для тейк-профита
        self.tp_patterns = [
            r'(?:tp|target|тейк|take\s*profit)\s*(?:at|в|:)?\s*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*(?:tp|target|тейк)',
            r'take\s*profit\s*(\d+(?:\.\d+)?)',
            r'target\s*(\d+(?:\.\d+)?)',
        ]
        
        # Паттерны для риска
        self.risk_patterns = [
            r'(?:risk|риск)\s*(?:=|\:)?\s*(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*%\s*(?:risk|риск)',
            r'r\s*(\d+(?:\.\d+)?)',
        ]
        
        # Паттерны для плеча
        self.leverage_patterns = [
            r'(?:lev|leverage|плечо)\s*(?:=|\:)?\s*(\d+)x',
            r'(\d+)x\s*(?:lev|leverage|плечо)',
            r'(\d+)\s*leverage',
        ]
        
        # Паттерны для символов
        self.symbol_patterns = [
            r'\b(btc|bitcoin|биткоин)\b',
            r'\b(eth|ethereum|эфир)\b',
            r'\b(sol|solana)\b',
            r'\b(ada|cardano)\b',
            r'\b(dot|polkadot)\b',
        ]

    def parse(self, text: str) -> Optional[ParsedSignal]:
        """Парсинг текста сигнала"""
        text_lower = text.lower()
        
        # Определяем направление
        direction = self._parse_direction(text_lower)
        if not direction:
            return None
        
        # Определяем символ
        symbol = self._parse_symbol(text_lower)
        if not symbol:
            symbol = "BTCUSDT"  # По умолчанию
        
        # Парсим цены
        entry_low, entry_high = self._parse_entry_zone(text_lower)
        stop_loss = self._parse_stop_loss(text_lower)
        take_profit = self._parse_take_profit(text_lower)
        take_profit2 = self._parse_take_profit2(text_lower)
        
        # Парсим риск и плечо
        risk_percent = self._parse_risk(text_lower)
        leverage = self._parse_leverage(text_lower)
        
        # Рассчитываем уверенность
        confidence = self._calculate_confidence(
            text_lower, direction, entry_low, entry_high, stop_loss
        )
        
        if confidence < 0.3:  # Минимальный порог уверенности
            return None
            
        return ParsedSignal(
            direction=direction,
            symbol=symbol,
            entry_low=entry_low,
            entry_high=entry_high,
            stop_loss=stop_loss,
            take_profit=take_profit,
            take_profit2=take_profit2,
            risk_percent=risk_percent,
            leverage=leverage,
            confidence=confidence
        )

    def _parse_direction(self, text: str) -> Optional[str]:
        """Парсинг направления"""
        buy_score = 0
        sell_score = 0
        
        for pattern in self.buy_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                buy_score += 1
        
        for pattern in self.sell_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                sell_score += 1
        
        if buy_score > sell_score:
            return "BUY"
        elif sell_score > buy_score:
            return "SELL"
        return None

    def _parse_symbol(self, text: str) -> Optional[str]:
        """Парсинг символа"""
        symbol_map = {
            'btc': 'BTCUSDT',
            'bitcoin': 'BTCUSDT',
            'биткоин': 'BTCUSDT',
            'eth': 'ETHUSDT',
            'ethereum': 'ETHUSDT',
            'эфир': 'ETHUSDT',
            'sol': 'SOLUSDT',
            'solana': 'SOLUSDT',
            'ada': 'ADAUSDT',
            'cardano': 'ADAUSDT',
            'dot': 'DOTUSDT',
            'polkadot': 'DOTUSDT',
        }
        
        for pattern, symbol in symbol_map.items():
            if re.search(rf'\b{pattern}\b', text, re.IGNORECASE):
                return symbol
        return None

    def _parse_entry_zone(self, text: str) -> Tuple[float, float]:
        """Парсинг зоны входа"""
        for pattern in self.entry_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                low = float(match.group(1))
                high = float(match.group(2))
                return low, high
        
        # Если зона не найдена, ищем отдельные цены
        prices = self._extract_prices(text)
        if len(prices) >= 2:
            return min(prices[:2]), max(prices[:2])
        
        return 0.0, 0.0

    def _parse_stop_loss(self, text: str) -> float:
        """Парсинг стоп-лосса"""
        for pattern in self.sl_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1))
        return 0.0

    def _parse_take_profit(self, text: str) -> Optional[float]:
        """Парсинг первого тейк-профита"""
        for pattern in self.tp_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1))
        return None

    def _parse_take_profit2(self, text: str) -> Optional[float]:
        """Парсинг второго тейк-профита"""
        # Ищем второй тейк-профит (обычно указывается как tp2 или target2)
        tp2_patterns = [
            r'tp2\s*(?:at|в|:)?\s*(\d+(?:\.\d+)?)',
            r'target2\s*(?:at|в|:)?\s*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*tp2',
        ]
        
        for pattern in tp2_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1))
        return None

    def _parse_risk(self, text: str) -> Optional[float]:
        """Парсинг процента риска"""
        for pattern in self.risk_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1))
        return None

    def _parse_leverage(self, text: str) -> Optional[int]:
        """Парсинг плеча"""
        for pattern in self.leverage_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None

    def _extract_prices(self, text: str) -> list:
        """Извлечение всех цен из текста"""
        prices = []
        for pattern in self.price_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    price = float(match)
                    if price > 0:
                        prices.append(price)
                except ValueError:
                    continue
        return sorted(prices)

    def _calculate_confidence(self, text: str, direction: str, 
                            entry_low: float, entry_high: float, 
                            stop_loss: float) -> float:
        """Расчет уверенности в парсинге"""
        confidence = 0.0
        
        # Базовые баллы
        if direction:
            confidence += 0.3
        
        if entry_low > 0 and entry_high > 0:
            confidence += 0.3
        
        if stop_loss > 0:
            confidence += 0.2
        
        # Дополнительные баллы за наличие ключевых слов
        if re.search(r'\b(entry|вход|зона|zone)\b', text, re.IGNORECASE):
            confidence += 0.1
        
        if re.search(r'\b(sl|stop|стоп)\b', text, re.IGNORECASE):
            confidence += 0.1
        
        return min(confidence, 1.0)

# Глобальный экземпляр парсера
parser = SignalParser()
