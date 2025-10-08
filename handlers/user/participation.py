from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import logging
from config import MAX_MAIN_PARTICIPANTS, MAX_RESERVE_PARTICIPANTS
from services.participation_service import ParticipationService
from services.tournament_service import TournamentService
from services.user_service import UserService

logger = logging.getLogger(__name__)

async def join_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик участия в турнире"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        tournament_id = int(query.data.split("_")[1])
        
        # Проверяем, зарегистрирован ли пользователь в системе
        if not UserService.is_user_registered(user_id):
            await query.edit_message_text(
                "Для участия в турнирах необходимо зарегистрироваться.\n"
                "Используйте команду /start"
            )
            return
        
        # Проверяем, не записан ли уже
        if ParticipationService.is_user_registered(user_id, tournament_id):
            keyboard = [
                [InlineKeyboardButton("Отменить участие", callback_data=f"leave_{tournament_id}")],
                [InlineKeyboardButton("← Назад к турниру", callback_data=f"tournament_{tournament_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "Вы уже записаны на этот турнир!\n\n"
                "Хотите отменить участие?",
                reply_markup=reply_markup
            )
            return
        
        # Пытаемся записать на турнир со статусом pending
        success = ParticipationService.add_participant_pending(user_id, tournament_id)
        
        if success:
            from config import PAYMENT_TIMEOUT_MINUTES
            
            tournament = TournamentService.get_tournament_by_id(tournament_id)
            
            keyboard = [
                [InlineKeyboardButton("Отменить участие", callback_data=f"leave_{tournament_id}")],
                [InlineKeyboardButton("← Назад к турниру", callback_data=f"tournament_{tournament_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"Заявка отправлена!\n\n"
                f"Турнир: {tournament['name']}\n"
                f"Статус: Ожидает одобрения\n\n"
                f"У вас есть {PAYMENT_TIMEOUT_MINUTES} минут для оплаты.\n"
                f"После оплаты дождитесь подтверждения от организатора.\n\n"
                f"Ссылка для оплаты:\n"
                f"https://pay.kaspi.kz/pay/g6b21oa4",
                reply_markup=reply_markup
            )
        else:
            keyboard = [
                [InlineKeyboardButton("← Назад к турниру", callback_data=f"tournament_{tournament_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "К сожалению, все места на турнире заняты!",
                reply_markup=reply_markup
            )
        
    except Exception as e:
        logger.error(f"Error in join_tournament: {e}")
        await query.edit_message_text("Произошла ошибка при записи на турнир")

async def leave_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик отмены участия в турнире"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        tournament_id = int(query.data.split("_")[1])
        
        success = ParticipationService.remove_participant(user_id, tournament_id)
        
        if success:
            keyboard = [
                [InlineKeyboardButton("← Назад к турниру", callback_data=f"tournament_{tournament_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "Ваше участие в турнире отменено.",
                reply_markup=reply_markup
            )
            
            
        else:
            keyboard = [
                [InlineKeyboardButton("← Назад к турниру", callback_data=f"tournament_{tournament_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "Ошибка при отмене участия.",
                reply_markup=reply_markup
            )
        
    except Exception as e:
        logger.error(f"Error in leave_tournament: {e}")
        await query.edit_message_text("Произошла ошибка")

async def handle_pending_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия на кнопку pending статуса"""
    query = update.callback_query
    await query.answer("Дождитесь окончания времени оплаты или одобрения организатора", show_alert=True)

async def handle_confirmed_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия на кнопку confirmed статуса"""
    query = update.callback_query
    await query.answer("Вы уже записаны на турнир!", show_alert=True)