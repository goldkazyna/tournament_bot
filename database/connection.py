import sqlite3
import logging
from config import DATABASE_PATH
import os

logger = logging.getLogger(__name__)

class DatabaseConnection:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self._ensure_db_directory()
        self._init_database()
    
    def _ensure_db_directory(self):
        """Создаем папку для БД если её нет"""
        db_dir = os.path.dirname(self.db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
    
    def _init_database(self):
        """Инициализация БД с базовой таблицей"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Таблица пользователей
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        telegram_id INTEGER UNIQUE NOT NULL,
                        full_name TEXT NOT NULL,
                        phone_number TEXT NOT NULL,
                        skill_level TEXT NOT NULL,
                        age_category TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Таблица турниров
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS tournaments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        date TEXT NOT NULL,
                        location TEXT NOT NULL,
                        format_info TEXT NOT NULL,
                        entry_fee TEXT NOT NULL,
                        description TEXT NOT NULL,
                        created_by INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status TEXT DEFAULT 'active'
                    )
                ''')
                # Таблица участий в турнирах
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS participations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        tournament_id INTEGER NOT NULL,
                        status TEXT DEFAULT 'pending',
                        registration_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        payment_deadline TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (telegram_id),
                        FOREIGN KEY (tournament_id) REFERENCES tournaments (id),
                        UNIQUE(user_id, tournament_id)
                    )
                ''')
                conn.commit()
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise
    def get_connection(self):
        """Получить соединение с БД"""
        return sqlite3.connect(self.db_path)

# Создаем глобальный экземпляр
db = DatabaseConnection()