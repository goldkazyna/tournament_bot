import logging
from database.connection import db
from telegram.ext import Application
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from services.tournament_service import TournamentService
from services.participation_service import ParticipationService
from config import MAX_MAIN_PARTICIPANTS, MAX_RESERVE_PARTICIPANTS

logger = logging.getLogger(__name__)

class SyncService:
    
    @staticmethod
    def get_tournament_viewers(tournament_id: int):
        """Получить всех кто смотрел этот турнир (заглушка)"""
        # В реальности здесь будет отслеживание кто открывал турнир
        # Пока возвращаем всех зарегистрированных пользователей
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT telegram_id FROM users")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting viewers: {e}")
            return []
    
    @staticmethod
    async def update_tournament_for_all(application: Application, tournament_id: int):
        """Обновить информацию о турнире у всех пользователей"""
        try:
            viewers = SyncService.get_tournament_viewers(tournament_id)
            tournament = TournamentService.get_tournament_by_id(tournament_id)
            
            if not tournament:
                return
            
            # Получаем данные об участниках
            counts = ParticipationService.get_participants_count(tournament_id)
            participants = ParticipationService.get_tournament_participants(tournament_id)

            # Формируем текст
            text = f"🏆 {tournament['name']}\n\n"
            text += f"📅 {tournament['date']}\n"
            text += f"📍 {tournament['location']}\n"
            text += f"✅ {tournament['format_info']}\n"
            text += f"💳 {tournament['entry_fee']}\n\n"
            text += f"👥 Участники: {counts['main']}/{MAX_MAIN_PARTICIPANTS} основных\n"
            text += f"📋 Резерв: {counts['reserve']}/{MAX_RESERVE_PARTICIPANTS}\n\n"

            if participants:
                text += "📝 ЗАПИСАВШИЕСЯ:\n"
                for participant in participants:
                    text += f"{participant['position']}. {participant['name']} ({participant['type']})\n"
                text += "\n"
            else:
                text += "📝 ЗАПИСАВШИЕСЯ:\nПока никого нет\n\n"

            text += f"📝 ОПИСАНИЕ:\n{tournament['description']}\n\n"
            
            # Отправляем обновления всем (кроме текущего пользователя)
            success_count = 0
            for user_id in viewers:
                try:
                    # Определяем кнопку для каждого пользователя
                    is_registered = ParticipationService.is_user_registered(user_id, tournament_id)
                    total_available = counts['available_main'] + counts['available_reserve']

                    if is_registered:
                        button_text = "❌ ОТМЕНИТЬ УЧАСТИЕ"
                        button_callback = f"leave_{tournament_id}"
                    elif total_available > 0:
                        if counts['available_main'] > 0:
                            button_text = "🟢 УЧАСТВОВАТЬ В ТУРНИРЕ"
                        else:
                            button_text = "🟡 УЧАСТВОВАТЬ (в резерв)"
                        button_callback = f"join_{tournament_id}"
                    else:
                        button_text = "🔴 МЕСТ НЕТ"
                        button_callback = f"no_slots_{tournament_id}"

                    keyboard = [
                        [InlineKeyboardButton(button_text, callback_data=button_callback)],
                        [InlineKeyboardButton("← Назад к списку", callback_data="back_to_tournaments")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await application.bot.send_message(
                        chat_id=user_id,
                        text=f"🔄 Обновление турнира:\n\n{text}",
                        reply_markup=reply_markup
                    )
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to update tournament for user {user_id}: {e}")
            
            logger.info(f"Tournament updated for {success_count} users")
            return success_count
            
        except Exception as e:
            logger.error(f"Error updating tournament: {e}")
            return 0