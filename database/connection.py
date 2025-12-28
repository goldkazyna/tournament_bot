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
            # МИГРАЦИЯ 3: Добавление tournament_type в tournaments
            # ========================================
            cursor.execute("PRAGMA table_info(tournaments)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'tournament_type' not in columns:
                logger.info("Migration: Adding tournament_type column to tournaments table")
                cursor.execute("ALTER TABLE tournaments ADD COLUMN tournament_type TEXT DEFAULT 'single'")
                logger.info("✅ Migration complete: tournament_type column added to tournaments")
            else:
                logger.info("⏭️ Migration skipped: tournament_type already exists in tournaments")
            
            # ========================================
            # МИГРАЦИЯ 4: Создание таблицы pairs для парных турниров
            # ========================================
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='pairs'
            """)
            
            if not cursor.fetchone():
                logger.info("Migration: Creating pairs table for double tournaments")
                cursor.execute('''
                    CREATE TABLE pairs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tournament_id INTEGER NOT NULL,
                        player1_id INTEGER NOT NULL,
                        player2_id INTEGER NOT NULL,
                        pair_number INTEGER,
                        status TEXT DEFAULT 'pending',
                        registration_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        payment_deadline TIMESTAMP,
                        FOREIGN KEY (tournament_id) REFERENCES tournaments (id),
                        FOREIGN KEY (player1_id) REFERENCES users (telegram_id),
                        FOREIGN KEY (player2_id) REFERENCES users (telegram_id),
                        UNIQUE(tournament_id, player1_id),
                        UNIQUE(tournament_id, player2_id)
                    )
                ''')
                logger.info("✅ Migration complete: pairs table created")
            else:
                logger.info("⏭️ Migration skipped: pairs table already exists")
            
            # ========================================
            # МИГРАЦИЯ 5: Исправление структуры pairs (если была старая версия)
            # ========================================
            cursor.execute("PRAGMA table_info(pairs)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Проверяем есть ли старые названия колонок
            if 'captain_user_id' in columns or 'partner_user_id' in columns:
                logger.info("Migration: Fixing pairs table structure (renaming columns)")
                
                # Создаём новую таблицу с правильной структурой
                cursor.execute('''
                    CREATE TABLE pairs_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tournament_id INTEGER NOT NULL,
                        player1_id INTEGER NOT NULL,
                        player2_id INTEGER NOT NULL,
                        pair_number INTEGER,
                        status TEXT DEFAULT 'pending',
                        registration_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        payment_deadline TIMESTAMP,
                        FOREIGN KEY (tournament_id) REFERENCES tournaments (id),
                        FOREIGN KEY (player1_id) REFERENCES users (telegram_id),
                        FOREIGN KEY (player2_id) REFERENCES users (telegram_id),
                        UNIQUE(tournament_id, player1_id),
                        UNIQUE(tournament_id, player2_id)
                    )
                ''')
                
                # Копируем данные из старой таблицы (если есть)
                try:
                    # Определяем какие колонки использовать
                    old_player1 = 'captain_user_id' if 'captain_user_id' in columns else 'player1_id'
                    old_player2 = 'partner_user_id' if 'partner_user_id' in columns else 'player2_id'
                    old_pair_number = 'position' if 'position' in columns else 'pair_number'
                    old_status = 'pair_status' if 'pair_status' in columns else 'status'
                    
                    cursor.execute(f'''
                        INSERT INTO pairs_new (id, tournament_id, player1_id, player2_id, pair_number, status, registration_time, payment_deadline)
                        SELECT id, tournament_id, {old_player1}, {old_player2}, {old_pair_number}, {old_status}, registration_time, payment_deadline
                        FROM pairs
                    ''')
                    logger.info(f"Copied {cursor.rowcount} pairs from old table")
                except Exception as e:
                    logger.warning(f"No data to copy from old pairs table: {e}")
                
                # Удаляем старую таблицу
                cursor.execute('DROP TABLE pairs')
                
                # Переименовываем новую
                cursor.execute('ALTER TABLE pairs_new RENAME TO pairs')
                
                logger.info("✅ Migration complete: pairs table structure fixed")
            else:
                logger.info("⏭️ Migration skipped: pairs table already has correct structure")
            
            logger.info("All migrations checked and applied successfully")
            
        except Exception as e:
            logger.error(f"Migration error: {e}")
            raise
    
    def get_connection(self):
        """Получить соединение с БД"""
        return sqlite3.connect(self.db_path)

# Создаем глобальный экземпляр
db = DatabaseConnection()