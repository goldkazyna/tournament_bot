from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import logging
from services.tournament_service import TournamentService
from services.participation_service import ParticipationService
from handlers.admin.panel import is_admin, is_super_admin, is_moderator
from utils.admin_keyboards import get_admin_panel_keyboard, get_moderator_panel_keyboard

logger = logging.getLogger(__name__)

async def show_moderation_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню модерации - выбор турнира"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if not is_admin(user_id):
            await query.edit_message_text("Нет прав доступа")
            return
        
        tournaments = TournamentService.get_all_tournaments()
        
        if not tournaments:
            # ИСПРАВЛЕНИЕ: Возвращаем правильную клавиатуру в зависимости от роли
            keyboard = [[InlineKeyboardButton("← Назад", callback_data="admin_panel_return")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "Нет активных турниров для модерации",
                reply_markup=reply_markup
            )
            return
        
        text = "Выберите турнир для модерации:\n\n"
        keyboard = []
        
        for tournament in tournaments:
            pending_count = len(ParticipationService.get_pending_participations(tournament['id']))
            
            text += f"{tournament['name']} - {pending_count} заявок\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"{tournament['name']} ({pending_count})", 
                    callback_data=f"moderate_{tournament['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("← Назад", callback_data="admin_panel_return")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in show_moderation_menu: {e}")
        await query.edit_message_text("Произошла ошибка")

async def show_tournament_moderation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать pending заявки конкретного турнира"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if not is_admin(user_id):
            await query.edit_message_text("Нет прав доступа")
            return
        
        tournament_id = int(query.data.split("_")[1])
        tournament = TournamentService.get_tournament_by_id(tournament_id)
        pending_participants = ParticipationService.get_pending_participations(tournament_id)
        
        if not pending_participants:
            keyboard = [[InlineKeyboardButton("← К списку турниров", callback_data="admin_moderation")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"Турнир: {tournament['name']}\n\n"
                "Нет заявок, ожидающих модерации",
                reply_markup=reply_markup
            )
            return
        
        text = f"Турнир: {tournament['name']}\n"
        text += f"Заявок на модерацию: {len(pending_participants)}\n\n"
        text += "Выберите участника:\n\n"
        
        keyboard = []
        
        for participant in pending_participants:
            from datetime import datetime
            deadline = datetime.fromisoformat(participant['payment_deadline'])
            remaining = deadline - datetime.now()
            remaining_minutes = int(remaining.total_seconds() / 60)
            
            if remaining_minutes <= 0:
                time_text = "Просрочено"
            else:
                time_text = f"{remaining_minutes} мин"
            
            text += f"{participant['name']} - {time_text}\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"{participant['name']} ({time_text})",
                    callback_data=f"participant_{participant['participation_id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("← К списку турниров", callback_data="admin_moderation")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in show_tournament_moderation: {e}")
        await query.edit_message_text("Произошла ошибка")

async def show_participant_moderation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать детали участника с кнопками одобрить/отклонить"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if not is_admin(user_id):
            await query.edit_message_text("Нет прав доступа")
            return
        
        participation_id = int(query.data.split("_")[1])
        
        # Получаем данные участника
        from database.connection import db
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.id, u.full_name, u.phone_number, p.registration_time, 
                       p.payment_deadline, t.name as tournament_name, p.tournament_id
                FROM participations p
                JOIN users u ON p.user_id = u.telegram_id
                JOIN tournaments t ON p.tournament_id = t.id
                WHERE p.id = ?
            """, (participation_id,))
            
            result = cursor.fetchone()
            
            if not result:
                await query.edit_message_text("Участник не найден")
                return
        
        from datetime import datetime
        deadline = datetime.fromisoformat(result[4])
        remaining = deadline - datetime.now()
        remaining_minutes = int(remaining.total_seconds() / 60)
        
        text = f"Участник: {result[1]}\n"
        text += f"Телефон: {result[2]}\n"
        text += f"Турнир: {result[5]}\n"
        text += f"Время подачи: {result[3][:16]}\n"
        
        if remaining_minutes <= 0:
            text += f"Статус: Просрочено ({abs(remaining_minutes)} мин назад)\n"
        else:
            text += f"Осталось времени: {remaining_minutes} минут\n"
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{participation_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{participation_id}")
            ],
            [InlineKeyboardButton("← Назад к турниру", callback_data=f"moderate_{result[6]}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in show_participant_moderation: {e}")
        await query.edit_message_text("Произошла ошибка")

async def approve_participant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Одобрить участника"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if not is_admin(user_id):
            await query.edit_message_text("Нет прав доступа")
            return
        
        participation_id = int(query.data.split("_")[1])
        
        # Получаем данные перед одобрением для уведомления
        from database.connection import db
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.user_id, t.name, t.id
                FROM participations p
                JOIN tournaments t ON p.tournament_id = t.id
                WHERE p.id = ?
            """, (participation_id,))
            
            result = cursor.fetchone()
            if not result:
                await query.edit_message_text("Участник не найден")
                return
            
            participant_user_id, tournament_name, tournament_id = result
        
        success = ParticipationService.approve_participation(participation_id)
        
        if success:
            # Отправляем уведомление пользователю
            try:
                await context.bot.send_message(
                    chat_id=participant_user_id,
                    text=f"✅ Ваше участие подтверждено!\n\n"
                         f"Турнир: {tournament_name}\n"
                         f"Статус: Одобрено организатором\n\n"
                         f"Увидимся на турнире! 🏆"
                )
            except Exception as e:
                logger.error(f"Failed to send approval notification to {participant_user_id}: {e}")
            
            # Добавляем кнопку админ панель
            from utils.admin_keyboards import get_admin_panel_keyboard, get_admin_panel_text
            keyboard = [
                [InlineKeyboardButton("🛠️ Админ панель", callback_data="admin_panel_return")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "✅ Участник одобрен!\n\n"
                "Уведомление отправлено.",
                reply_markup=reply_markup
            )
            
        else:
            await query.edit_message_text("Ошибка при одобрении участника")
        
    except Exception as e:
        logger.error(f"Error in approve_participant: {e}")
        await query.edit_message_text("Произошла ошибка")

async def reject_participant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отклонить участника"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if not is_admin(user_id):
            await query.edit_message_text("Нет прав доступа")
            return
        
        participation_id = int(query.data.split("_")[1])
        
        # Получаем данные перед отклонением для уведомления
        from database.connection import db
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.user_id, t.name, t.id
                FROM participations p
                JOIN tournaments t ON p.tournament_id = t.id
                WHERE p.id = ?
            """, (participation_id,))
            
            result = cursor.fetchone()
            if not result:
                await query.edit_message_text("Участник не найден")
                return
            
            participant_user_id, tournament_name, tournament_id = result
        
        success = ParticipationService.reject_participation(participation_id)
        
        if success:
            # Отправляем уведомление пользователю
            try:
                keyboard = [
                    [InlineKeyboardButton(
                        "Попробовать записаться снова", 
                        callback_data=f"tournament_{tournament_id}"
                    )]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_message(
                    chat_id=participant_user_id,
                    text=f"❌ Ваша заявка отклонена\n\n"
                         f"Турнир: {tournament_name}\n"
                         f"Причина: Не поступила оплата в срок или другие причины\n\n"
                         f"Вы можете подать заявку повторно.",
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.error(f"Failed to send rejection notification to {participant_user_id}: {e}")
            
            # Добавляем кнопку админ панель
            keyboard = [
                [InlineKeyboardButton("🛠️ Админ панель", callback_data="admin_panel_return")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "❌ Участник отклонен!\n\n"
                "Место освобождено. Уведомление отправлено.",
                reply_markup=reply_markup
            )
            
        else:
            await query.edit_message_text("Ошибка при отклонении участника")
        
    except Exception as e:
        logger.error(f"Error in reject_participant: {e}")
        await query.edit_message_text("Произошла ошибка")