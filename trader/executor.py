# trader/executor.py
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging
from risk.manager import build_order_plan, OrderPlan
from market.bitget_client import bitget_client
from nlp.parser_rules import parser, ParsedSignal
import time

logger = logging.getLogger(__name__)

@dataclass
class ExecutedOrder:
    """Результат выполнения ордера"""
    order_id: str
    symbol: str
    side: str
    price: float
    qty: float
    status: str
    order_type: str
    reduce_only: bool = False

class Executor:
    """Исполнитель торговых операций"""
    
    def __init__(self, bitget_trader=None, dry_run: bool = True):
        self.bitget_trader = bitget_trader
        self.dry_run = dry_run
        self.client = bitget_client
    
    def plan_from_signal(self, signal, context: Dict[str, Any]) -> OrderPlan:
        """
        Создание плана торговли из сигнала
        
        Args:
            signal: Объект сигнала
            context: Контекст с параметрами (source, equity_sub, etc.)
            
        Returns:
            OrderPlan с детальным планом торговли
        """
        try:
            # Парсим сигнал если это текст
            if hasattr(signal, 'raw_text') and signal.raw_text:
                parsed = parser.parse(signal.raw_text)
                if not parsed:
                    raise ValueError("Не удалось распарсить сигнал")
                
                # Используем данные из парсера
                side = parsed.direction
                entry_zone = [parsed.entry_low, parsed.entry_high]
                stop_loss = parsed.stop_loss
                tp_levels = []
                if parsed.take_profit:
                    tp_levels.append(parsed.take_profit)
                if parsed.take_profit2:
                    tp_levels.append(parsed.take_profit2)
                
                # Если тейк-профиты не указаны, рассчитываем по R:R
                if not tp_levels:
                    entry_price = (entry_zone[0] + entry_zone[1]) / 2
                    risk_distance = abs(entry_price - stop_loss)
                    if side == "BUY":
                        tp_levels = [
                            entry_price + risk_distance * 2,  # R:R = 2:1
                            entry_price + risk_distance * 3   # R:R = 3:1
                        ]
                    else:
                        tp_levels = [
                            entry_price - risk_distance * 2,
                            entry_price - risk_distance * 3
                        ]
            else:
                # Используем данные из объекта сигнала
                side = getattr(signal, 'position_type', 'BUY')
                entry_zone = [
                    getattr(signal, 'entry_low', 0),
                    getattr(signal, 'entry_high', 0)
                ]
                stop_loss = getattr(signal, 'stop_loss', 0)
                tp_levels = getattr(signal, 'take_profits', [])
                
                # Если зона входа не указана, используем одну цену
                if entry_zone[0] == 0 and entry_zone[1] == 0:
                    entry_price = getattr(signal, 'entry_price', 0)
                    if entry_price > 0:
                        entry_zone = [entry_price * 0.999, entry_price * 1.001]
            
            # Проверяем валидность данных
            if not all(entry_zone) or stop_loss <= 0:
                raise ValueError("Невалидные цены входа или стоп-лосса")
            
            # Строим план
            plan = build_order_plan(
                source=context.get('source', 'INTRADAY'),
                side=side,
                entry_zone=entry_zone,
                stop_loss=stop_loss,
                tp_levels=tp_levels,
                legs="1/2",  # Пока используем 1/2
                leverage_hint=context.get('leverage_min', 10)
            )
            
            logger.info(f"План создан: {side} {plan.symbol} @ {entry_zone}")
            return plan
            
        except Exception as e:
            logger.error(f"Ошибка создания плана: {e}")
            raise
    
    def place_all(self, plan: OrderPlan) -> tuple[List[ExecutedOrder], dict]:
        """
        Размещение всех ордеров по плану
        
        Args:
            plan: План торговли
            
        Returns:
            Tuple[список размещенных ордеров, план с plan_id]
        """
        orders = []
        
        try:
            # 1. Устанавливаем плечо
            self._set_leverage(plan.symbol, plan.leg1.leverage)
            
            # 2. Размещаем ордера входа (первая нога)
            entry_order = self._place_entry_order(plan, plan.leg1)
            if entry_order:
                orders.append(entry_order)
            
            # 3. Размещаем стоп-лосс
            sl_order = self._place_stop_loss(plan, plan.leg1)
            if sl_order:
                orders.append(sl_order)
            
            # 4. Размещаем тейк-профиты
            tp_orders = self._place_take_profits(plan, plan.leg1)
            orders.extend(tp_orders)
            
            # 5. Преобразуем OrderPlan в dict для watcher
            plan_dict = {
                'symbol': plan.symbol,
                'side': plan.side,
                'entry': plan.entry_price,
                'stop': plan.sl_price,
                'tps': plan.tp_levels,
                'tp_shares': plan.tp_shares,
                'breakeven_after_tp': plan.move_sl_to_be_after_tp,
                'plan_id': getattr(plan, 'plan_id', None),
                'qty_total': plan.leg1.qty + (plan.leg2.qty if plan.leg2 else 0.0)
            }
            
            logger.info(f"Размещено {len(orders)} ордеров")
            return orders, plan_dict
            
        except Exception as e:
            logger.error(f"Ошибка размещения ордеров: {e}")
            # Возвращаем пустой план в случае ошибки
            plan_dict = {
                'symbol': plan.symbol,
                'side': plan.side,
                'entry': plan.entry_price,
                'stop': plan.sl_price,
                'tps': plan.tp_levels,
                'tp_shares': plan.tp_shares,
                'breakeven_after_tp': plan.move_sl_to_be_after_tp,
                'plan_id': getattr(plan, 'plan_id', None)
            }
            return orders, plan_dict
    
    def _set_leverage(self, symbol: str, leverage: int):
        """Установка плеча"""
        try:
            if not self.dry_run:
                result = self.client.set_leverage(symbol, leverage)
                if result.get('code') == '00000':
                    logger.info(f"Плечо установлено: {leverage}x")
                else:
                    logger.warning(f"Ошибка установки плеча: {result}")
            else:
                logger.info(f"DRY_RUN: Установка плеча {leverage}x для {symbol}")
        except Exception as e:
            logger.error(f"Ошибка установки плеча: {e}")
    
    def _place_entry_order(self, plan: OrderPlan, leg) -> Optional[ExecutedOrder]:
        """Размещение ордера входа"""
        try:
            if plan.entry_type == "limit_zone":
                # Лимитный ордер в зоне
                price = plan.entry_price
                order_data = {
                    'symbol': plan.symbol,
                    'marginCoin': 'USDT',
                    'side': plan.side.lower(),
                    'orderType': 'limit',
                    'size': str(leg.qty),
                    'price': str(price),
                    'timeInForceValue': 'normal',
                    'reduceOnly': False
                }
            else:
                # Рыночный ордер
                order_data = {
                    'symbol': plan.symbol,
                    'marginCoin': 'USDT',
                    'side': plan.side.lower(),
                    'orderType': 'market',
                    'size': str(leg.qty),
                    'reduceOnly': False
                }
            
            if not self.dry_run:
                result = self.client.place_order(order_data)
                if result.get('code') == '00000':
                    data = result.get('data', {})
                    return ExecutedOrder(
                        order_id=data.get('orderId', ''),
                        symbol=plan.symbol,
                        side=plan.side,
                        price=float(data.get('price', 0)),
                        qty=leg.qty,
                        status='NEW',
                        order_type=plan.entry_type,
                        reduce_only=False
                    )
            else:
                logger.info(f"DRY_RUN: Размещение ордера входа {order_data}")
                return ExecutedOrder(
                    order_id=f"dry_run_entry_{int(time.time())}",
                    symbol=plan.symbol,
                    side=plan.side,
                    price=plan.entry_price or 0,
                    qty=leg.qty,
                    status='NEW',
                    order_type=plan.entry_type,
                    reduce_only=False
                )
                
        except Exception as e:
            logger.error(f"Ошибка размещения ордера входа: {e}")
            return None
    
    def _place_stop_loss(self, plan: OrderPlan, leg) -> Optional[ExecutedOrder]:
        """Размещение стоп-лосса"""
        try:
            order_data = {
                'symbol': plan.symbol,
                'marginCoin': 'USDT',
                'side': 'sell' if plan.side == 'BUY' else 'buy',
                'orderType': 'stop',
                'size': str(leg.qty),
                'triggerPrice': str(plan.sl_price),
                'reduceOnly': True
            }
            
            if not self.dry_run:
                result = self.client.place_order(order_data)
                if result.get('code') == '00000':
                    data = result.get('data', {})
                    return ExecutedOrder(
                        order_id=data.get('orderId', ''),
                        symbol=plan.symbol,
                        side='SELL' if plan.side == 'BUY' else 'BUY',
                        price=plan.sl_price,
                        qty=leg.qty,
                        status='NEW',
                        order_type='stop',
                        reduce_only=True
                    )
            else:
                logger.info(f"DRY_RUN: Размещение стоп-лосса {order_data}")
                return ExecutedOrder(
                    order_id=f"dry_run_sl_{int(time.time())}",
                    symbol=plan.symbol,
                    side='SELL' if plan.side == 'BUY' else 'BUY',
                    price=plan.sl_price,
                    qty=leg.qty,
                    status='NEW',
                    order_type='stop',
                    reduce_only=True
                )
                
        except Exception as e:
            logger.error(f"Ошибка размещения стоп-лосса: {e}")
            return None
    
    def _place_take_profits(self, plan: OrderPlan, leg) -> List[ExecutedOrder]:
        """Размещение тейк-профитов"""
        orders = []
        
        try:
            for i, (tp_price, tp_share) in enumerate(zip(plan.tp_levels, plan.tp_shares)):
                if tp_share <= 0 or tp_price <= 0:
                    continue
                
                qty = leg.qty * tp_share
                if qty <= 0:
                    continue
                
                order_data = {
                    'symbol': plan.symbol,
                    'marginCoin': 'USDT',
                    'side': 'sell' if plan.side == 'BUY' else 'buy',
                    'orderType': 'limit',
                    'size': str(qty),
                    'price': str(tp_price),
                    'timeInForceValue': 'normal',
                    'reduceOnly': True
                }
                
                if not self.dry_run:
                    result = self.client.place_order(order_data)
                    if result.get('code') == '00000':
                        data = result.get('data', {})
                        orders.append(ExecutedOrder(
                            order_id=data.get('orderId', ''),
                            symbol=plan.symbol,
                            side='SELL' if plan.side == 'BUY' else 'BUY',
                            price=tp_price,
                            qty=qty,
                            status='NEW',
                            order_type='limit',
                            reduce_only=True
                        ))
                else:
                    logger.info(f"DRY_RUN: Размещение TP{i+1} {order_data}")
                    orders.append(ExecutedOrder(
                        order_id=f"dry_run_tp{i+1}_{int(time.time())}",
                        symbol=plan.symbol,
                        side='SELL' if plan.side == 'BUY' else 'BUY',
                        price=tp_price,
                        qty=qty,
                        status='NEW',
                        order_type='limit',
                        reduce_only=True
                    ))
                    
        except Exception as e:
            logger.error(f"Ошибка размещения тейк-профитов: {e}")
        
        return orders

# Глобальный экземпляр исполнителя
executor = Executor()
