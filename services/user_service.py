import sqlite3
import logging
from database.connection import db
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class UserService:
    
    @staticmethod
    def is_user_registered(telegram_id: int) -> bool:
        """Проверяем, зарегистрирован ли пользователь"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
                result = cursor.fetchone()
                return result is not None
        except Exception as e:
            logger.error(f"Error checking user registration: {e}")
            return False
    
    @staticmethod
    def get_user_by_telegram_id(telegram_id: int) -> Optional[Dict]:
        """Получаем пользователя по telegram_id"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, telegram_id, full_name, phone_number, 
                           skill_level, age_category, created_at 
                    FROM users WHERE telegram_id = ?
                """, (telegram_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'id': result[0],
                        'telegram_id': result[1],
                        'full_name': result[2],
                        'phone_number': result[3],
                        'skill_level': result[4],
                        'age_category': result[5],
                        'created_at': result[6]
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    @staticmethod
    def register_user(telegram_id: int, full_name: str, phone_number: str, 
                     skill_level: str, age_category: str) -> bool:
        """Регистрируем нового пользователя"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (telegram_id, full_name, phone_number, 
                                     skill_level, age_category)
                    VALUES (?, ?, ?, ?, ?)
                """, (telegram_id, full_name, phone_number, skill_level, age_category))
                
                conn.commit()
                logger.info(f"User {telegram_id} registered successfully")
                return True
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            return False

    @staticmethod
    def update_user_name(telegram_id: int, new_name: str) -> bool:
        """Обновить ФИО пользователя"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users SET full_name = ? WHERE telegram_id = ?
                """, (new_name, telegram_id))
                
                conn.commit()
                logger.info(f"User {telegram_id} name updated to {new_name}")
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating user name: {e}")
            return False