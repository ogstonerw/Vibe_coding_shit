from typing import List, Optional, Dict, Any
from datetime import datetime
import json
from storage.db import db

class PositionRepository:
    """Репозиторий для работы с позициями"""
    
    def create(self, data: Dict[str, Any]) -> int:
        """Создать новую позицию"""
        return db.insert('positions', data)
    
    def get_by_id(self, position_id: int) -> Optional[Dict[str, Any]]:
        """Получить позицию по ID"""
        return db.fetch_one(
            "SELECT * FROM positions WHERE id = ?", 
            (position_id,)
        )
    
    def get_by_signal_id(self, signal_id: str) -> Optional[Dict[str, Any]]:
        """Получить позицию по signal_id"""
        return db.fetch_one(
            "SELECT * FROM positions WHERE signal_id = ?", 
            (signal_id,)
        )
    
    def get_by_state(self, state: str) -> List[Dict[str, Any]]:
        """Получить позиции по состоянию"""
        return db.fetch_all(
            "SELECT * FROM positions WHERE state = ? ORDER BY created_at DESC", 
            (state,)
        )
    
    def get_active_positions(self) -> List[Dict[str, Any]]:
        """Получить все активные позиции"""
        return db.fetch_all(
            """
            SELECT * FROM positions 
            WHERE state NOT IN ('CLOSED', 'CANCELED') 
            ORDER BY created_at DESC
            """
        )
    
    def update_state(self, position_id: int, new_state: str) -> int:
        """Обновить состояние позиции"""
        return db.update(
            'positions', 
            {'state': new_state}, 
            'id = ?', 
            (position_id,)
        )
    
    def update_position(self, position_id: int, data: Dict[str, Any]) -> int:
        """Обновить позицию"""
        return db.update('positions', data, 'id = ?', (position_id,))
    
    def get_recent_positions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Получить последние позиции"""
        return db.fetch_all(
            "SELECT * FROM positions ORDER BY created_at DESC LIMIT ?", 
            (limit,)
        )

class OrderRepository:
    """Репозиторий для работы с ордерами"""
    
    def create(self, data: Dict[str, Any]) -> int:
        """Создать новый ордер"""
        return db.insert('orders', data)
    
    def get_by_id(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Получить ордер по ID"""
        return db.fetch_one(
            "SELECT * FROM orders WHERE id = ?", 
            (order_id,)
        )
    
    def get_by_position_id(self, position_id: int) -> List[Dict[str, Any]]:
        """Получить ордера позиции"""
        return db.fetch_all(
            "SELECT * FROM orders WHERE position_id = ? ORDER BY created_at", 
            (position_id,)
        )
    
    def get_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Получить ордера по статусу"""
        return db.fetch_all(
            "SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC", 
            (status,)
        )
    
    def update_status(self, order_id: int, new_status: str, order_id_external: Optional[str] = None) -> int:
        """Обновить статус ордера"""
        data = {'status': new_status}
        if order_id_external:
            data['order_id'] = order_id_external
        return db.update('orders', data, 'id = ?', (order_id,))
    
    def update_order(self, order_id: int, data: Dict[str, Any]) -> int:
        """Обновить ордер"""
        return db.update('orders', data, 'id = ?', (order_id,))

class FillRepository:
    """Репозиторий для работы с исполнениями"""
    
    def create(self, data: Dict[str, Any]) -> int:
        """Создать новое исполнение"""
        return db.insert('fills', data)
    
    def get_by_order_id(self, order_id: int) -> List[Dict[str, Any]]:
        """Получить исполнения ордера"""
        return db.fetch_all(
            "SELECT * FROM fills WHERE order_id = ? ORDER BY ts", 
            (order_id,)
        )
    
    def get_by_position_id(self, position_id: int) -> List[Dict[str, Any]]:
        """Получить исполнения позиции"""
        return db.fetch_all(
            "SELECT * FROM fills WHERE position_id = ? ORDER BY ts", 
            (position_id,)
        )

class StatsRepository:
    """Репозиторий для работы со статистикой"""
    
    def create(self, data: Dict[str, Any]) -> int:
        """Создать новую статистику"""
        return db.insert('stats', data)
    
    def get_by_position_id(self, position_id: int) -> Optional[Dict[str, Any]]:
        """Получить статистику позиции"""
        return db.fetch_one(
            "SELECT * FROM stats WHERE position_id = ?", 
            (position_id,)
        )
    
    def update_stats(self, position_id: int, data: Dict[str, Any]) -> int:
        """Обновить статистику"""
        return db.update('stats', data, 'position_id = ?', (position_id,))
    
    def get_overall_stats(self) -> Dict[str, Any]:
        """Получить общую статистику"""
        sql = """
        SELECT 
            COUNT(*) as total_trades,
            SUM(CASE WHEN win = 1 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN win = 0 THEN 1 ELSE 0 END) as losses,
            SUM(pnl_usdt) as total_pnl,
            AVG(pnl_pct) as avg_pnl_pct,
            SUM(CASE WHEN win = 1 THEN pnl_usdt ELSE 0 END) as total_wins,
            SUM(CASE WHEN win = 0 THEN pnl_usdt ELSE 0 END) as total_losses
        FROM stats
        WHERE closed_at IS NOT NULL
        """
        result = db.fetch_one(sql)
        if result:
            total_trades = result['total_trades']
            wins = result['wins']
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            result['win_rate'] = round(win_rate, 2)
        return result or {}
    
    def get_recent_performance(self, days: int = 30) -> List[Dict[str, Any]]:
        """Получить производительность за последние дни"""
        sql = """
        SELECT 
            DATE(closed_at) as date,
            COUNT(*) as trades,
            SUM(CASE WHEN win = 1 THEN 1 ELSE 0 END) as wins,
            SUM(pnl_usdt) as daily_pnl,
            AVG(pnl_pct) as avg_pnl_pct
        FROM stats
        WHERE closed_at >= date('now', '-{} days')
        GROUP BY DATE(closed_at)
        ORDER BY date DESC
        """.format(days)
        return db.fetch_all(sql)

# Глобальные экземпляры репозиториев
position_repo = PositionRepository()
order_repo = OrderRepository()
fill_repo = FillRepository()
stats_repo = StatsRepository()
