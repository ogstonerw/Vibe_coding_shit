import sqlite3
import os
from typing import Optional
from contextlib import contextmanager
from config.settings import settings

class Database:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.behavior.db_path
        self._ensure_db_directory()
        self._init_database()

    def _ensure_db_directory(self):
        """Создаем директорию для базы данных если её нет"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

    def _init_database(self):
        """Инициализация базы данных"""
        with self.get_connection() as conn:
            # Читаем и выполняем миграции
            migrations_path = os.path.join(os.path.dirname(__file__), 'migrations.sql')
            with open(migrations_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            
            # Выполняем миграции
            conn.executescript(sql_script)
            conn.commit()

    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для получения соединения с БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Возвращаем результаты как словари
        try:
            yield conn
        finally:
            conn.close()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Выполнить SQL запрос"""
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor

    def execute_many(self, sql: str, params_list: list) -> sqlite3.Cursor:
        """Выполнить SQL запрос с множественными параметрами"""
        with self.get_connection() as conn:
            cursor = conn.executemany(sql, params_list)
            conn.commit()
            return cursor

    def fetch_one(self, sql: str, params: tuple = ()) -> Optional[dict]:
        """Получить одну запись"""
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            row = cursor.fetchone()
            return dict(row) if row else None

    def fetch_all(self, sql: str, params: tuple = ()) -> list:
        """Получить все записи"""
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def insert(self, table: str, data: dict) -> int:
        """Вставить запись и вернуть ID"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        with self.get_connection() as conn:
            cursor = conn.execute(sql, tuple(data.values()))
            conn.commit()
            return cursor.lastrowid

    def update(self, table: str, data: dict, where: str, where_params: tuple = ()) -> int:
        """Обновить записи"""
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
        params = tuple(data.values()) + where_params
        
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor.rowcount

    def delete(self, table: str, where: str, where_params: tuple = ()) -> int:
        """Удалить записи"""
        sql = f"DELETE FROM {table} WHERE {where}"
        
        with self.get_connection() as conn:
            cursor = conn.execute(sql, where_params)
            conn.commit()
            return cursor.rowcount

    def table_exists(self, table_name: str) -> bool:
        """Проверить существование таблицы"""
        sql = """
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
        """
        result = self.fetch_one(sql, (table_name,))
        return result is not None

    def get_table_info(self, table_name: str) -> list:
        """Получить информацию о структуре таблицы"""
        sql = f"PRAGMA table_info({table_name})"
        return self.fetch_all(sql)

# Глобальный экземпляр базы данных
db = Database()
