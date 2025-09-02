import time
import hmac
import hashlib
import requests
import json
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class BitgetClient:
    """Клиент для работы с Bitget API"""
    
    def __init__(self):
        self.api_key = settings.bitget.api_key
        self.api_secret = settings.bitget.api_secret
        self.passphrase = settings.bitget.passphrase
        self.base_url = settings.bitget.base_url
        self.market = settings.bitget.market
        self.symbol = settings.bitget.symbol
        self.dry_run = settings.behavior.dry_run
        
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'ACCESS-KEY': self.api_key,
            'ACCESS-PASSPHRASE': self.passphrase
        })
    
    def _generate_signature(self, timestamp: str, method: str, request_path: str, body: str = '') -> str:
        """Генерация подписи для API запросов"""
        message = timestamp + method + request_path + body
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Dict[str, Any]:
        """Выполнение HTTP запроса к API"""
        url = f"{self.base_url}{endpoint}"
        timestamp = str(int(time.time() * 1000))
        
        # Подготовка параметров
        if params:
            query_string = urlencode(params)
            endpoint_with_params = f"{endpoint}?{query_string}"
        else:
            endpoint_with_params = endpoint
        
        # Подготовка тела запроса
        body = json.dumps(data) if data else ''
        
        # Генерация подписи
        signature = self._generate_signature(timestamp, method, endpoint_with_params, body)
        
        # Установка заголовков
        headers = {
            'ACCESS-SIGN': signature,
            'ACCESS-TIMESTAMP': timestamp,
            'ACCESS-KEY': self.api_key,
            'ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
        
        try:
            if method == 'GET':
                response = self.session.get(url, params=params, headers=headers)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = self.session.delete(url, json=data, headers=headers)
            else:
                raise ValueError(f"Неподдерживаемый метод: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка API запроса: {e}")
            return {'error': str(e)}
    
    def get_account_info(self) -> Dict[str, Any]:
        """Получение информации об аккаунте"""
        if self.dry_run:
            return {
                'code': '00000',
                'data': {
                    'totalEquity': settings.risk.equity_usdt,
                    'availableBalance': settings.risk.equity_usdt * 0.9,
                    'marginBalance': settings.risk.equity_usdt
                }
            }
        
        return self._make_request('GET', '/api/mix/v1/account/account')
    
    def get_positions(self, symbol: str = None) -> Dict[str, Any]:
        """Получение открытых позиций"""
        if self.dry_run:
            return {
                'code': '00000',
                'data': []
            }
        
        params = {'symbol': symbol or self.symbol}
        return self._make_request('GET', '/api/mix/v1/position/singlePosition', params)
    
    def get_ticker(self, symbol: str = None) -> Dict[str, Any]:
        """Получение текущей цены"""
        params = {'symbol': symbol or self.symbol}
        return self._make_request('GET', '/api/mix/v1/market/ticker', params)
    
    def get_orderbook(self, symbol: str = None, limit: int = 20) -> Dict[str, Any]:
        """Получение стакана заявок"""
        params = {
            'symbol': symbol or self.symbol,
            'limit': limit
        }
        return self._make_request('GET', '/api/mix/v1/market/depth', params)
    
    def place_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Размещение ордера"""
        if self.dry_run:
            logger.info(f"DRY_RUN: Размещение ордера {order_data}")
            return {
                'code': '00000',
                'data': {
                    'orderId': f"dry_run_{int(time.time())}",
                    'clientOid': order_data.get('clientOid', ''),
                    'symbol': order_data.get('symbol'),
                    'side': order_data.get('side'),
                    'orderType': order_data.get('orderType'),
                    'price': order_data.get('price'),
                    'size': order_data.get('size')
                }
            }
        
        return self._make_request('POST', '/api/mix/v1/order/placeOrder', data=order_data)
    
    def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Отмена ордера"""
        if self.dry_run:
            logger.info(f"DRY_RUN: Отмена ордера {order_id}")
            return {
                'code': '00000',
                'data': {
                    'orderId': order_id,
                    'symbol': symbol
                }
            }
        
        data = {
            'symbol': symbol,
            'orderId': order_id
        }
        return self._make_request('POST', '/api/mix/v1/order/cancelOrder', data=data)
    
    def get_order_status(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Получение статуса ордера"""
        if self.dry_run:
            return {
                'code': '00000',
                'data': {
                    'orderId': order_id,
                    'symbol': symbol,
                    'status': 'new',
                    'filledSize': '0',
                    'price': '0'
                }
            }
        
        params = {
            'symbol': symbol,
            'orderId': order_id
        }
        return self._make_request('GET', '/api/mix/v1/order/detail', params)
    
    def get_open_orders(self, symbol: str = None) -> Dict[str, Any]:
        """Получение открытых ордеров"""
        if self.dry_run:
            return {
                'code': '00000',
                'data': []
            }
        
        params = {'symbol': symbol or self.symbol}
        return self._make_request('GET', '/api/mix/v1/order/current', params)
    
    def get_order_history(self, symbol: str = None, limit: int = 100) -> Dict[str, Any]:
        """Получение истории ордеров"""
        if self.dry_run:
            return {
                'code': '00000',
                'data': []
            }
        
        params = {
            'symbol': symbol or self.symbol,
            'limit': limit
        }
        return self._make_request('GET', '/api/mix/v1/order/history', params)
    
    def set_leverage(self, symbol: str, leverage: int, margin_coin: str = 'USDT') -> Dict[str, Any]:
        """Установка плеча"""
        if self.dry_run:
            logger.info(f"DRY_RUN: Установка плеча {leverage}x для {symbol}")
            return {
                'code': '00000',
                'data': {
                    'symbol': symbol,
                    'leverage': leverage,
                    'marginCoin': margin_coin
                }
            }
        
        data = {
            'symbol': symbol,
            'leverage': leverage,
            'marginCoin': margin_coin
        }
        return self._make_request('POST', '/api/mix/v1/account/setLeverage', data=data)
    
    def get_market_data(self, symbol: str = None, granularity: str = '1m', limit: int = 100) -> Dict[str, Any]:
        """Получение исторических данных"""
        params = {
            'symbol': symbol or self.symbol,
            'granularity': granularity,
            'limit': limit
        }
        return self._make_request('GET', '/api/mix/v1/market/candles', params)
    
    def create_limit_order(self, symbol: str, side: str, size: float, price: float, 
                          reduce_only: bool = False, time_in_force: str = 'normal') -> Dict[str, Any]:
        """Создание лимитного ордера"""
        order_data = {
            'symbol': symbol,
            'marginCoin': 'USDT',
            'side': side.lower(),
            'orderType': 'limit',
            'size': str(size),
            'price': str(price),
            'timeInForceValue': time_in_force,
            'reduceOnly': reduce_only
        }
        
        return self.place_order(order_data)
    
    def create_market_order(self, symbol: str, side: str, size: float, 
                           reduce_only: bool = False) -> Dict[str, Any]:
        """Создание рыночного ордера"""
        order_data = {
            'symbol': symbol,
            'marginCoin': 'USDT',
            'side': side.lower(),
            'orderType': 'market',
            'size': str(size),
            'reduceOnly': reduce_only
        }
        
        return self.place_order(order_data)
    
    def create_stop_order(self, symbol: str, side: str, size: float, trigger_price: float,
                         order_price: float = None, reduce_only: bool = False) -> Dict[str, Any]:
        """Создание стоп-ордера"""
        order_data = {
            'symbol': symbol,
            'marginCoin': 'USDT',
            'side': side.lower(),
            'orderType': 'stop',
            'size': str(size),
            'triggerPrice': str(trigger_price),
            'reduceOnly': reduce_only
        }
        
        if order_price:
            order_data['orderPrice'] = str(order_price)
        
        return self.place_order(order_data)

# Глобальный экземпляр клиента
bitget_client = BitgetClient()
