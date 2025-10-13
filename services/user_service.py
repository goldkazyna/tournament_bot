import sqlite3
import logging
from database.connection import db
from typing import Optional, Dict
from datetime import datetime

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
                           skill_level, age_category, created_at,
                           player_level, player_level_updated_at, player_level_updated_by
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
                        'created_at': result[6],
                        'player_level': result[7],
                        'player_level_updated_at': result[8],
                        'player_level_updated_by': result[9]
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
    
    # ===============================
    # НОВЫЕ МЕТОДЫ ДЛЯ РАБОТЫ С УРОВНЯМИ
    # ===============================
    
    @staticmethod
    def set_player_level(telegram_id: int, level_code: str, admin_id: int) -> bool:
        """
        Установить уровень игрока
        
        Args:
            telegram_id (int): Telegram ID пользователя
            level_code (str): Код уровня, например "3.5"
            admin_id (int): Telegram ID админа, который установил уровень
        
        Returns:
            bool: True если успешно, False если ошибка
        """
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users 
                    SET player_level = ?,
                        player_level_updated_at = ?,
                        player_level_updated_by = ?
                    WHERE telegram_id = ?
                """, (level_code, datetime.now(), admin_id, telegram_id))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Player level set: user={telegram_id}, level={level_code}, by_admin={admin_id}")
                    return True
                else:
                    logger.warning(f"User {telegram_id} not found when setting player level")
                    return False
                    
        except Exception as e:
            logger.error(f"Error setting player level: {e}")
            return False
    
    @staticmethod
    def get_player_level(telegram_id: int) -> Optional[str]:
        """
        Получить уровень игрока
        
        Args:
            telegram_id (int): Telegram ID пользователя
        
        Returns:
            str: Код уровня, например "3.5", или None если не установлен
        """
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT player_level FROM users WHERE telegram_id = ?
                """, (telegram_id,))
                
                result = cursor.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            logger.error(f"Error getting player level: {e}")
            return None
    
    @staticmethod
    def reset_player_level(telegram_id: int, admin_id: int) -> bool:
        """
        Сбросить уровень игрока (установить NULL)
        
        Args:
            telegram_id (int): Telegram ID пользователя
            admin_id (int): Telegram ID админа
        
        Returns:
            bool: True если успешно, False если ошибка
        """
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users 
                    SET player_level = NULL,
                        player_level_updated_at = ?,
                        player_level_updated_by = ?
                    WHERE telegram_id = ?
                """, (datetime.now(), admin_id, telegram_id))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Player level reset: user={telegram_id}, by_admin={admin_id}")
                    return True
                else:
                    return False
                    
        except Exception as e:
            logger.error(f"Error resetting player level: {e}")
            return False
    
    @staticmethod
    def get_all_users() -> list:
        """
        Получить список всех пользователей (для экспорта или списков)
        
        Returns:
            list: Список словарей с данными пользователей
        """
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT telegram_id, full_name, phone_number, 
                           player_level, created_at
                    FROM users
                    WHERE telegram_id > 0
                    ORDER BY created_at DESC
                """)
                
                results = cursor.fetchall()
                users = []
                
                for row in results:
                    users.append({
                        'telegram_id': row[0],
                        'full_name': row[1],
                        'phone_number': row[2],
                        'player_level': row[3],
                        'created_at': row[4]
                    })
                
                return users
                
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    @staticmethod
    def search_user_by_id(telegram_id: int) -> Optional[Dict]:
        """
        Поиск пользователя по Telegram ID (алиас для get_user_by_telegram_id)
        Для удобства использования в админке
        
        Args:
            telegram_id (int): Telegram ID для поиска
        
        Returns:
            dict: Данные пользователя или None если не найден
        """
        return UserService.get_user_by_telegram_id(telegram_id)