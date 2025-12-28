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
            logger.warning(f"🔍 Tournament {tournament['id']}: name={tournament['name']}, type={tournament.get('tournament_type')}")
            if tournament.get('tournament_type') == 'double':
                # Парный турнир - считаем пары
                from services.pair_service import PairService
                all_pairs = PairService.get_tournament_pairs(tournament['id'])
                pending_count = len([p for p in all_pairs if p.get('status') == 'pending'])
                
                logger.info(f"Tournament {tournament['id']}: total pairs={len(all_pairs)}, pending={pending_count}")  # ← ОТЛАДКА
            # ============================================
            else:
                # Одиночный турнир - считаем участников
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
        if tournament.get('tournament_type') == 'double':
            # Парный турнир - показываем пары
            await show_pair_tournament_moderation(query, tournament_id, tournament)
            return
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
        from config import MAX_MAIN_PARTICIPANTS
        
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
            # Определяем позицию участника (основной или резерв)
            participants = ParticipationService.get_tournament_participants(tournament_id)
            
            # Ищем позицию одобренного участника
            user_position = None
            for participant in participants:
                # Сравниваем по user_id из БД
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT telegram_id FROM users 
                        WHERE full_name = ? AND phone_number = ?
                    """, (participant['name'], participant['phone']))
                    user_result = cursor.fetchone()
                    
                    if user_result and user_result[0] == participant_user_id:
                        user_position = participant['position']
                        break
            
            # Отправляем уведомление в зависимости от позиции
            try:
                if user_position and user_position <= MAX_MAIN_PARTICIPANTS:
                    # Основной участник
                    await context.bot.send_message(
                        chat_id=participant_user_id,
                        text=f"✅ Ваше участие подтверждено!\n\n"
                             f"Турнир: {tournament_name}\n"
                             f"Статус: Основной участник #{user_position}\n\n"
                             f"Оплата получена. Ждём вас на турнире! 🏆"
                    )
                else:
                    # Резервист
                    await context.bot.send_message(
                        chat_id=participant_user_id,
                        text=f"✅ Ваша заявка одобрена!\n\n"
                             f"Турнир: {tournament_name}\n"
                             f"Статус: Резервный участник\n\n"
                             f"📋 Вы в списке резерва. Если освободится место среди основных участников, "
                             f"мы сразу же сообщим вам лично!\n\n"
                             f"Следите за уведомлениями 📱"
                    )
            except Exception as e:
                logger.error(f"Failed to send approval notification to {participant_user_id}: {e}")
            
            # Добавляем кнопку админ панель
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
        
        # ============================================
        # НОВОЕ: Проверяем был ли турнир полным ДО отклонения
        # ============================================
        from services.tournament_service import TournamentService
        from services.participation_service import ParticipationService
        from config import MAX_MAIN_PARTICIPANTS
        
        tournament = TournamentService.get_tournament_by_id(tournament_id)
        counts_before = ParticipationService.get_participants_count(tournament_id)
        was_full = counts_before['available_main'] == 0
        
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
            
            # ============================================
            # НОВОЕ: Если турнир был полным - уведомляем канал
            # ============================================
            if was_full:
                import asyncio
                from services.notification_service import NotificationService
                
                asyncio.create_task(
                    NotificationService.notify_slot_available(
                        context.application, tournament
                    )
                )
                logger.info(f"Moderator rejected participant from full tournament {tournament_id}, notifying channel about free slot")
            
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
        
async def show_pair_tournament_moderation(query, tournament_id: int, tournament: dict):
    """Показать pending пары для модерации"""
    try:
        from services.pair_service import PairService
        from datetime import datetime
        
        pairs = PairService.get_tournament_pairs(tournament_id)
        pending_pairs = [p for p in pairs if p['status'] == 'pending']
        
        if not pending_pairs:
            keyboard = [[InlineKeyboardButton("← К списку турниров", callback_data="admin_moderation")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"Турнир: {tournament['name']} (ПАРНЫЙ)\n\n"
                "Нет пар, ожидающих модерации",
                reply_markup=reply_markup
            )
            return
        
        text = f"Турнир: {tournament['name']} (ПАРНЫЙ)\n"
        text += f"Пар на модерацию: {len(pending_pairs)}\n\n"
        text += "Выберите пару:\n\n"
        
        keyboard = []
        
        for pair in pending_pairs:
            deadline = datetime.fromisoformat(pair['payment_deadline'])
            remaining = deadline - datetime.now()
            remaining_minutes = int(remaining.total_seconds() / 60)
            
            if remaining_minutes <= 0:
                time_text = "Просрочено"
            else:
                time_text = f"{remaining_minutes} мин"
            
            pair_text = f"Пара {pair['pair_number']}: {pair['player1_name']} / {pair['player2_name']}"
            text += f"{pair_text} - {time_text}\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"{pair_text} ({time_text})",
                    callback_data=f"pair_{pair['pair_id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("← К списку турниров", callback_data="admin_moderation")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in show_pair_tournament_moderation: {e}")
        await query.edit_message_text("Произошла ошибка")


async def show_pair_moderation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать детали пары с кнопками одобрить/отклонить"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if not is_admin(user_id):
            await query.edit_message_text("Нет прав доступа")
            return
        
        pair_id = int(query.data.split("_")[1])
        
        # Получаем данные пары
        from database.connection import db
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.id, p.tournament_id, p.player1_id, p.player2_id,
                       u1.full_name as player1_name, u1.phone_number as player1_phone,
                       u2.full_name as player2_name, u2.phone_number as player2_phone,
                       p.registration_time, p.payment_deadline, t.name as tournament_name
                FROM pairs p
                JOIN users u1 ON p.player1_id = u1.telegram_id
                JOIN users u2 ON p.player2_id = u2.telegram_id
                JOIN tournaments t ON p.tournament_id = t.id
                WHERE p.id = ?
            """, (pair_id,))
            
            result = cursor.fetchone()
            
            if not result:
                await query.edit_message_text("Пара не найдена")
                return
        
        from datetime import datetime
        deadline = datetime.fromisoformat(result[9])
        remaining = deadline - datetime.now()
        remaining_minutes = int(remaining.total_seconds() / 60)
        
        text = f"👥 Пара на модерацию\n\n"
        text += f"Турнир: {result[10]}\n\n"
        text += f"Игрок 1: {result[4]}\n"
        text += f"Телефон: {result[5]}\n\n"
        text += f"Игрок 2: {result[6]}\n"
        text += f"Телефон: {result[7]}\n\n"
        text += f"Время подачи: {result[8][:16]}\n"
        
        if remaining_minutes <= 0:
            text += f"Статус: ⏰ Просрочено ({abs(remaining_minutes)} мин назад)\n"
        else:
            text += f"Осталось времени: ⏰ {remaining_minutes} минут\n"
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Одобрить пару", callback_data=f"approve_pair_{pair_id}"),
                InlineKeyboardButton("❌ Отклонить пару", callback_data=f"reject_pair_{pair_id}")
            ],
            [InlineKeyboardButton("← Назад к турниру", callback_data=f"moderate_{result[1]}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in show_pair_moderation: {e}")
        await query.edit_message_text("Произошла ошибка")


async def approve_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Одобрить пару"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if not is_admin(user_id):
            await query.edit_message_text("Нет прав доступа")
            return
        
        pair_id = int(query.data.split("_")[2])
        
        # Получаем данные перед одобрением для уведомления
        from database.connection import db
        from services.pair_service import PairService
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.player1_id, p.player2_id, t.name, t.id, p.pair_number,
                       u1.full_name as player1_name, u2.full_name as player2_name
                FROM pairs p
                JOIN tournaments t ON p.tournament_id = t.id
                JOIN users u1 ON p.player1_id = u1.telegram_id
                JOIN users u2 ON p.player2_id = u2.telegram_id
                WHERE p.id = ?
            """, (pair_id,))
            
            result = cursor.fetchone()
            if not result:
                await query.edit_message_text("Пара не найдена")
                return
            
            player1_id, player2_id, tournament_name, tournament_id, pair_number, player1_name, player2_name = result
        
        success = PairService.approve_pair(pair_id)
        
        if success:
            # Определяем тип пары (основная или резерв)
            from config import MAX_PAIR_SLOTS
            
            if pair_number <= MAX_PAIR_SLOTS:
                pair_type = "основная"
            else:
                pair_type = "резервная"
            
            # Отправляем уведомления обоим игрокам
            try:
                await context.bot.send_message(
                    chat_id=player1_id,
                    text=f"✅ Ваша пара одобрена!\n\n"
                         f"Турнир: {tournament_name}\n"
                         f"Пара: {player1_name} / {player2_name}\n"
                         f"Статус: {pair_type.capitalize()} пара #{pair_number}\n\n"
                         f"Ждём вас на турнире! 🎾"
                )
            except Exception as e:
                logger.error(f"Failed to send approval notification to player1 {player1_id}: {e}")
            
            try:
                await context.bot.send_message(
                    chat_id=player2_id,
                    text=f"✅ Ваша пара одобрена!\n\n"
                         f"Турнир: {tournament_name}\n"
                         f"Пара: {player1_name} / {player2_name}\n"
                         f"Статус: {pair_type.capitalize()} пара #{pair_number}\n\n"
                         f"Ждём вас на турнире! 🎾"
                )
            except Exception as e:
                logger.error(f"Failed to send approval notification to player2 {player2_id}: {e}")
            
            keyboard = [
                [InlineKeyboardButton("🛠️ Админ панель", callback_data="admin_panel_return")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ Пара одобрена!\n\n"
                f"Игроки: {player1_name} / {player2_name}\n"
                f"Уведомления отправлены.",
                reply_markup=reply_markup
            )
            
        else:
            await query.edit_message_text("Ошибка при одобрении пары")
        
    except Exception as e:
        logger.error(f"Error in approve_pair: {e}")
        await query.edit_message_text("Произошла ошибка")


async def reject_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отклонить пару"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if not is_admin(user_id):
            await query.edit_message_text("Нет прав доступа")
            return
        
        pair_id = int(query.data.split("_")[2])
        
        # Получаем данные перед отклонением для уведомления
        from database.connection import db
        from services.pair_service import PairService
        from services.tournament_service import TournamentService
        from config import MAX_PAIR_SLOTS
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.player1_id, p.player2_id, t.name, t.id,
                       u1.full_name as player1_name, u2.full_name as player2_name
                FROM pairs p
                JOIN tournaments t ON p.tournament_id = t.id
                JOIN users u1 ON p.player1_id = u1.telegram_id
                JOIN users u2 ON p.player2_id = u2.telegram_id
                WHERE p.id = ?
            """, (pair_id,))
            
            result = cursor.fetchone()
            if not result:
                await query.edit_message_text("Пара не найдена")
                return
            
            player1_id, player2_id, tournament_name, tournament_id, player1_name, player2_name = result
        
        # Проверяем был ли турнир полным ДО отклонения
        tournament = TournamentService.get_tournament_by_id(tournament_id)
        counts_before = PairService.get_pairs_count(tournament_id)
        was_full = counts_before['available_main'] == 0
        
        success = PairService.reject_pair(pair_id)
        
        if success:
            # Отправляем уведомления обоим игрокам
            try:
                keyboard = [
                    [InlineKeyboardButton(
                        "Попробовать записаться снова", 
                        callback_data=f"tournament_{tournament_id}"
                    )]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_message(
                    chat_id=player1_id,
                    text=f"❌ Ваша заявка отклонена\n\n"
                         f"Турнир: {tournament_name}\n"
                         f"Пара: {player1_name} / {player2_name}\n"
                         f"Причина: Не поступила оплата в срок или другие причины\n\n"
                         f"Вы можете подать заявку повторно.",
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.error(f"Failed to send rejection notification to player1 {player1_id}: {e}")
            
            try:
                await context.bot.send_message(
                    chat_id=player2_id,
                    text=f"❌ Ваша заявка отклонена\n\n"
                         f"Турнир: {tournament_name}\n"
                         f"Пара: {player1_name} / {player2_name}\n"
                         f"Причина: Не поступила оплата в срок или другие причины\n\n"
                         f"Вы можете подать заявку повторно.",
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.error(f"Failed to send rejection notification to player2 {player2_id}: {e}")
            
            # Если турнир был полным - уведомляем канал
            if was_full:
                import asyncio
                from services.notification_service import NotificationService
                
                asyncio.create_task(
                    NotificationService.notify_slot_available(
                        context.application, tournament
                    )
                )
                logger.info(f"Moderator rejected pair from full tournament {tournament_id}, notifying channel about free slot")
            
            keyboard = [
                [InlineKeyboardButton("🛠️ Админ панель", callback_data="admin_panel_return")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"❌ Пара отклонена!\n\n"
                f"Игроки: {player1_name} / {player2_name}\n"
                f"Место освобождено. Уведомления отправлены.",
                reply_markup=reply_markup
            )
            
        else:
            await query.edit_message_text("Ошибка при отклонении пары")
        
    except Exception as e:
        logger.error(f"Error in reject_pair: {e}")
        await query.edit_message_text("Произошла ошибка")