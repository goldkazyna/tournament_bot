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
                
                # МИГРАЦИИ
                self._migrate_database(conn)
                
                conn.commit()
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    def _migrate_database(self, conn):
        """Миграции базы данных"""
        cursor = conn.cursor()
        
        try:
            logger.info("Checking for database migrations...")
            
            # ========================================
            # МИГРАЦИЯ 1: Добавление player_level в users
            # ========================================
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'player_level' not in columns:
                logger.info("Migration: Adding player_level columns to users table")
                cursor.execute("ALTER TABLE users ADD COLUMN player_level TEXT DEFAULT NULL")
                cursor.execute("ALTER TABLE users ADD COLUMN player_level_updated_at TIMESTAMP DEFAULT NULL")
                cursor.execute("ALTER TABLE users ADD COLUMN player_level_updated_by INTEGER DEFAULT NULL")
                logger.info("✅ Migration complete: player_level columns added to users")
            else:
                logger.info("⏭️ Migration skipped: player_level already exists in users")
            
            # ========================================
            # МИГРАЦИЯ 2: Добавление ограничений по уровню в tournaments
            # ========================================
            cursor.execute("PRAGMA table_info(tournaments)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'min_level' not in columns:
                logger.info("Migration: Adding level restriction columns to tournaments table")
                cursor.execute("ALTER TABLE tournaments ADD COLUMN min_level TEXT DEFAULT NULL")
                cursor.execute("ALTER TABLE tournaments ADD COLUMN max_level TEXT DEFAULT NULL")
                cursor.execute("ALTER TABLE tournaments ADD COLUMN level_restriction TEXT DEFAULT 'open'")
                logger.info("✅ Migration complete: level restriction columns added to tournaments")
            else:
                logger.info("⏭️ Migration skipped: level restrictions already exist in tournaments")
            
            # ========================================
            # МИГРАЦИЯ 3: Добавление tournament_type в tournaments (если не было)
            # ========================================
            cursor.execute("PRAGMA table_info(tournaments)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'tournament_type' not in columns:
                logger.info("Migration: Adding tournament_type column to tournaments table")
                cursor.execute("ALTER TABLE tournaments ADD COLUMN tournament_type TEXT DEFAULT 'single'")
                logger.info("✅ Migration complete: tournament_type column added to tournaments")
            else:
                logger.info("⏭️ Migration skipped: tournament_type already exists in tournaments")
            
            logger.info("All migrations checked and applied successfully")
            
        except Exception as e:
            logger.error(f"Migration error: {e}")
            raise
    
    def get_connection(self):
        """Получить соединение с БД"""
        return sqlite3.connect(self.db_path)

# Создаем глобальный экземпляр
db = DatabaseConnection()