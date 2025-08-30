# trader/router.py
from typing import Dict, Any, Optional
import logging
from nlp.parser_rules import parser, ParsedSignal
from risk.manager import build_order_plan, OrderPlan

logger = logging.getLogger(__name__)

class SignalRouter:
    """Маршрутизация сигналов между стратегиями"""
    
    def __init__(self):
        self.scalping_ratio = 0.15  # 15% для скальпинга
        self.intraday_ratio = 0.85  # 85% для интрадей
        
    def route_signal(self, signal_text: str, source: str) -> Dict[str, Any]:
        """
        Маршрутизация сигнала по типу стратегии
        
        Args:
            signal_text: Текст сигнала
            source: Источник сигнала (SCALPING/INTRADAY)
            
        Returns:
            Словарь с параметрами маршрутизации
        """
        try:
            # Парсим сигнал
            parsed = parser.parse(signal_text)
            if not parsed:
                logger.warning(f"Не удалось распарсить сигнал: {signal_text[:100]}...")
                return self._default_routing(source)
            
            # Определяем тип стратегии
            strategy_type = self._determine_strategy_type(parsed, source)
            
            # Рассчитываем параметры
            routing = {
                'strategy_type': strategy_type,
                'source': source,
                'parsed_signal': parsed,
                'risk_allocation': self._calculate_risk_allocation(strategy_type),
                'execution_params': self._get_execution_params(strategy_type)
            }
            
            logger.info(f"Сигнал направлен в {strategy_type} (источник: {source})")
            return routing
            
        except Exception as e:
            logger.error(f"Ошибка маршрутизации сигнала: {e}")
            return self._default_routing(source)
    
    def _determine_strategy_type(self, parsed: ParsedSignal, source: str) -> str:
        """Определение типа стратегии"""
        # Если источник явно указан, используем его
        if source.upper() == "SCALPING":
            return "SCALPING"
        elif source.upper() == "INTRADAY":
            return "INTRADAY"
        
        # Иначе определяем по характеристикам сигнала
        if self._is_scalping_signal(parsed):
            return "SCALPING"
        else:
            return "INTRADAY"
    
    def _is_scalping_signal(self, parsed: ParsedSignal) -> bool:
        """Определение скальпинг-сигнала по характеристикам"""
        # Критерии для скальпинга:
        # 1. Короткий стоп-лосс (менее 1% от цены входа)
        # 2. Быстрый тейк-профит (менее 2% от цены входа)
        # 3. Высокое плечо (более 20x)
        
        entry_price = (parsed.entry_low + parsed.entry_high) / 2
        stop_distance = abs(entry_price - parsed.stop_loss)
        stop_percent = (stop_distance / entry_price) * 100
        
        # Проверяем стоп-лосс
        if stop_percent < 1.0:
            return True
        
        # Проверяем тейк-профит
        if parsed.take_profit:
            tp_distance = abs(entry_price - parsed.take_profit)
            tp_percent = (tp_distance / entry_price) * 100
            if tp_percent < 2.0:
                return True
        
        # Проверяем плечо
        if parsed.leverage and parsed.leverage > 20:
            return True
        
        return False
    
    def _calculate_risk_allocation(self, strategy_type: str) -> Dict[str, float]:
        """Расчет распределения риска"""
        if strategy_type == "SCALPING":
            return {
                'scalping_pct': self.scalping_ratio * 100,
                'intraday_pct': 0.0
            }
        else:
            return {
                'scalping_pct': 0.0,
                'intraday_pct': self.intraday_ratio * 100
            }
    
    def _get_execution_params(self, strategy_type: str) -> Dict[str, Any]:
        """Получение параметров исполнения для стратегии"""
        if strategy_type == "SCALPING":
            return {
                'leverage_min': 15,
                'leverage_max': 25,
                'risk_leg_pct': 1.0,  # Меньший риск на ногу для скальпинга
                'timeout_minutes': 30,  # Короткий таймаут
                'entry_type': 'market',  # Быстрый вход
                'tp_strategy': 'quick'   # Быстрые тейки
            }
        else:
            return {
                'leverage_min': 10,
                'leverage_max': 20,
                'risk_leg_pct': 1.5,  # Стандартный риск
                'timeout_minutes': 240,  # Длинный таймаут
                'entry_type': 'limit_zone',  # Точный вход
                'tp_strategy': 'gradual'  # Постепенные тейки
            }
    
    def _default_routing(self, source: str) -> Dict[str, Any]:
        """Маршрутизация по умолчанию"""
        strategy_type = "SCALPING" if source.upper() == "SCALPING" else "INTRADAY"
        return {
            'strategy_type': strategy_type,
            'source': source,
            'parsed_signal': None,
            'risk_allocation': self._calculate_risk_allocation(strategy_type),
            'execution_params': self._get_execution_params(strategy_type)
        }
    
    def create_order_plan(self, routing: Dict[str, Any], equity_total: float) -> Optional[OrderPlan]:
        """
        Создание плана ордеров на основе маршрутизации
        
        Args:
            routing: Результат маршрутизации
            equity_total: Общий депозит
            
        Returns:
            План ордеров или None
        """
        try:
            parsed = routing.get('parsed_signal')
            if not parsed:
                logger.warning("Нет распарсенного сигнала для создания плана")
                return None
            
            # Рассчитываем поддепозит
            strategy_type = routing['strategy_type']
            if strategy_type == "SCALPING":
                equity_sub = equity_total * self.scalping_ratio
            else:
                equity_sub = equity_total * self.intraday_ratio
            
            # Получаем параметры исполнения
            exec_params = routing['execution_params']
            
            # Создаем план
            plan = build_order_plan(
                source=routing['source'],
                side=parsed.direction,
                entry_zone=[parsed.entry_low, parsed.entry_high],
                stop_loss=parsed.stop_loss,
                tp_levels=[parsed.take_profit] if parsed.take_profit else [],
                legs="1/2",
                leverage_hint=exec_params['leverage_min']
            )
            
            # Добавляем метаданные маршрутизации
            plan.meta.update({
                'strategy_type': strategy_type,
                'execution_params': exec_params,
                'equity_sub': equity_sub
            })
            
            return plan
            
        except Exception as e:
            logger.error(f"Ошибка создания плана ордеров: {e}")
            return None

# Глобальный экземпляр роутера
signal_router = SignalRouter()
