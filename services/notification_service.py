import logging
from database.connection import db
from telegram.ext import Application
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import random
from config import PRIORITY_CHAT_IDS, CHANNEL_ID  # ← ИЗМЕНИЛИ импорт!

logger = logging.getLogger(__name__)

class NotificationService:
    
    @staticmethod
    def get_all_registered_users():
        """Получить всех зарегистрированных пользователей (кроме системных)"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT telegram_id FROM users WHERE telegram_id > 0")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []
    
    @staticmethod
    async def notify_new_tournament(application: Application, tournament: dict):
        """Уведомить о новом турнире: сначала приоритетным, потом в канал"""
        try:
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
            
            # ============================================
            # ИЗМЕНИЛИ: URL кнопка вместо callback
            # ============================================
            bot_username = application.bot.username  # Получаем username бота
            keyboard = [
                [InlineKeyboardButton(
                    "📋 Подробнее о турнире", 
                    url=f"https://t.me/{bot_username}?start=tournament_{tournament['id']}"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # ============================================
            # Отправка приоритетным чатам сначала
            # ============================================
            priority_count = 0
            for priority_id in PRIORITY_CHAT_IDS:
                try:
                    await application.bot.send_message(
                        chat_id=priority_id,
                        text=text,
                        reply_markup=reply_markup
                    )
                    logger.info(f"✅ Priority notification sent to {priority_id}")
                    priority_count += 1
                except Exception as e:
                    logger.error(f"Failed to send priority notification to {priority_id}: {e}")
            
            if priority_count > 0:
                logger.info(f"⏳ Waiting 5 seconds before sending to channel...")
                await asyncio.sleep(5)
            
            # ============================================
            # Отправка в канал
            # ============================================
            try:
                await application.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=text,
                    reply_markup=reply_markup
                )
                logger.info(f"✅ Tournament notification sent to channel {CHANNEL_ID}")
            except Exception as e:
                logger.error(f"Failed to send notification to channel {CHANNEL_ID}: {e}")
                return 0
            
            logger.info(f"Tournament notification sent to {priority_count} priority chats + 1 channel")
            return priority_count + 1
            
        except Exception as e:
            logger.error(f"Error in notify_new_tournament: {e}")
            return 0
            
    @staticmethod
    async def notify_slot_available(application: Application, tournament: dict):
        """Уведомить канал о появлении свободного места"""
        try:
            from config import CHANNEL_ID
            
            text = (
                f"🔔 Освободилось место!\n\n"
                f"🏆 Турнир: {tournament['name']}\n"
                f"📅 {tournament['date']}\n"
                f"📍 {tournament['location']}\n\n"
                f"✅ Есть свободное место для участия!\n"
                f"Успейте зарегистрироваться!"
            )
            
            # Deep link на турнир
            bot_username = application.bot.username
            keyboard = [
                [InlineKeyboardButton(
                    "🎾 Записаться на турнир", 
                    url=f"https://t.me/{bot_username}?start=tournament_{tournament['id']}"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                await application.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=text,
                    reply_markup=reply_markup
                )
                logger.info(f"✅ Slot available notification sent to channel for tournament {tournament['id']}")
                return True
            except Exception as e:
                logger.error(f"Failed to send slot notification to channel: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error in notify_slot_available: {e}")
            return False