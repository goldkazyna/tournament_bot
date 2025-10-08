import logging
from database.connection import db
from telegram.ext import Application
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

class NotificationService:
    
    @staticmethod
    def get_all_registered_users():
        """Получить всех зарегистрированных пользователей (кроме системных)"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                # Исключаем системных пользователей с отрицательными ID
                cursor.execute("SELECT telegram_id FROM users WHERE telegram_id > 0")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []
    
    @staticmethod
    async def notify_new_tournament(application: Application, tournament: dict):
        """Уведомить всех о новом турнире"""
        try:
            user_ids = NotificationService.get_all_registered_users()
            
            text = (
                f"🎾 Новый турнир!\n\n"
                f"{tournament['name']}\n"
                f"{tournament['date']}\n"
                f"{tournament['location']}\n"
                f"{tournament['format_info']}\n"
                f"{tournament['entry_fee']}\n\n"
                f"👥 Места: 16 основных + 2 резерв\n\n"
                f"Регистрация открыта!"
            )
            
            keyboard = [
                [InlineKeyboardButton(
                    "📋 Подробнее о турнире", 
                    callback_data=f"tournament_{tournament['id']}"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            success_count = 0
            for user_id in user_ids:
                try:
                    await application.bot.send_message(
                        chat_id=user_id,
                        text=text,
                        reply_markup=reply_markup
                    )
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to send notification to {user_id}: {e}")
            
            logger.info(f"Tournament notification sent to {success_count}/{len(user_ids)} users")
            return success_count
            
        except Exception as e:
            logger.error(f"Error in notify_new_tournament: {e}")
            return 0