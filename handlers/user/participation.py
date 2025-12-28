from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import logging
from config import MAX_MAIN_PARTICIPANTS, MAX_RESERVE_PARTICIPANTS
from services.participation_service import ParticipationService
from services.tournament_service import TournamentService
from services.user_service import UserService

logger = logging.getLogger(__name__)

async def join_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик участия в турнире с проверкой уровня"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        tournament_id = int(query.data.split("_")[1])
        from services.tournament_service import TournamentService
        tournament = TournamentService.get_tournament_by_id(tournament_id)
        if tournament and tournament.get('tournament_type') == 'double':
            # Это парный турнир - вызываем парный обработчик
            from handlers.user.pair_participation import join_pair_tournament
            return await join_pair_tournament(update, context)

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
        
        # ============================================
        # НОВОЕ: ПРОВЕРКА УРОВНЯ ИГРОКА
        # ============================================
        
        from services.tournament_service import TournamentService
        from levels import check_level_in_range, get_level_name
        
        tournament = TournamentService.get_tournament_by_id(tournament_id)
        user_data = UserService.get_user_by_telegram_id(user_id)
        
        if not tournament:
            await query.edit_message_text("Турнир не найден")
            return
        
        # Проверяем ограничения по уровню
        if tournament.get('level_restriction') == 'restricted':
            player_level = user_data.get('player_level')
            min_level = tournament.get('min_level')
            max_level = tournament.get('max_level')
            
            # Проверка 1: Уровень не установлен
            if not player_level:
                keyboard = [
                    [InlineKeyboardButton("← Назад к турниру", callback_data=f"tournament_{tournament_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    "❌ Ваш уровень игры не установлен\n\n"
                    "Этот турнир имеет ограничения по уровню.\n"
                    f"Требуемый уровень: {min_level} - {max_level}\n\n"
                    "📱 Для установки вашего уровня свяжитесь с Кристианом:\n"
                    "WhatsApp: +7 771 175 4421",
                    reply_markup=reply_markup
                )
                return
            
            # Проверка 2: Уровень не подходит по диапазону
            if not check_level_in_range(player_level, min_level, max_level):
                player_level_name = get_level_name(player_level)
                min_level_name = get_level_name(min_level)
                max_level_name = get_level_name(max_level)
                
                keyboard = [
                    [InlineKeyboardButton("← Назад к турниру", callback_data=f"tournament_{tournament_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"❌ К сожалению, вы не можете участвовать в этом турнире\n\n"
                    f"Турнир: {tournament['name']}\n\n"
                    f"Требуемый уровень: {min_level} - {max_level}\n"
                    f"({min_level_name} - {max_level_name})\n\n"
                    f"Ваш уровень: {player_level} ({player_level_name})\n\n"
                    f"Ищите турниры, подходящие вашему уровню! 🎾",
                    reply_markup=reply_markup
                )
                return
        
        # Если турнир открытый ИЛИ уровень подходит - записываем
        
        # Пытаемся записать на турнир со статусом pending
        success = ParticipationService.add_participant_pending(user_id, tournament_id)
        
        if success:
            from config import PAYMENT_TIMEOUT_MINUTES
            
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
    """Запрос подтверждения отмены участия в турнире"""
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("leave_pair_"):
            from handlers.user.pair_participation import leave_pair_tournament
            return await leave_pair_tournament(update, context)
            
        tournament_id = int(query.data.split("_")[1])
        
        # Получаем информацию о турнире
        from services.tournament_service import TournamentService
        tournament = TournamentService.get_tournament_by_id(tournament_id)
        
        if not tournament:
            await query.edit_message_text("Турнир не найден")
            return
        
        # Спрашиваем подтверждение
        keyboard = [
            [InlineKeyboardButton("✅ Да, отменить участие", callback_data=f"confirm_leave_{tournament_id}")],
            [InlineKeyboardButton("❌ Нет, оставить участие", callback_data=f"cancel_leave_{tournament_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚠️ Подтверждение отмены\n\n"
            f"Турнир: {tournament['name']}\n\n"
            f"Вы уверены, что хотите отменить участие в этом турнире?",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in leave_tournament: {e}")
        await query.edit_message_text("Произошла ошибка")


async def confirm_leave_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждённая отмена участия в турнире"""
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("confirm_leave_pair_"):
            from handlers.user.pair_participation import confirm_leave_pair_tournament
            return await confirm_leave_pair_tournament(update, context)
            
        user_id = query.from_user.id
        tournament_id = int(query.data.split("_")[2])
        
        # Получаем информацию о турнире ДО удаления
        from services.tournament_service import TournamentService
        from services.participation_service import ParticipationService
        from config import MAX_MAIN_PARTICIPANTS
        
        tournament = TournamentService.get_tournament_by_id(tournament_id)
        counts_before = ParticipationService.get_participants_count(tournament_id)
        was_full = counts_before['available_main'] == 0  # ← Проверяем был ли турнир полным
        
        success = ParticipationService.remove_participant(user_id, tournament_id)
        
        if success:
            keyboard = [
                [InlineKeyboardButton("← Назад к турниру", callback_data=f"tournament_{tournament_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "✅ Ваше участие в турнире отменено.",
                reply_markup=reply_markup
            )
            
            # ============================================
            # НОВОЕ: Если турнир был полным - уведомляем канал
            # ============================================
            if was_full:
                import asyncio
                from services.notification_service import NotificationService
                
                # Отправляем в фоне
                asyncio.create_task(
                    NotificationService.notify_slot_available(
                        context.application, tournament
                    )
                )
                logger.info(f"Slot became available in tournament {tournament_id}, notifying channel")
        else:
            keyboard = [
                [InlineKeyboardButton("← Назад к турниру", callback_data=f"tournament_{tournament_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "❌ Ошибка при отмене участия.",
                reply_markup=reply_markup
            )
        
    except Exception as e:
        logger.error(f"Error in confirm_leave_tournament: {e}")
        await query.edit_message_text("Произошла ошибка")


async def cancel_leave_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена удаления - возврат к карточке турнира"""
    try:
        query = update.callback_query
        await query.answer("Участие сохранено")
        
        if query.data.startswith("cancel_leave_pair_"):
            from handlers.user.pair_participation import cancel_leave_pair_tournament
            return await cancel_leave_pair_tournament(update, context)
            
        tournament_id = int(query.data.split("_")[2])
        
        # Получаем данные турнира
        from services.tournament_service import TournamentService
        from services.participation_service import ParticipationService
        from config import MAX_MAIN_PARTICIPANTS, MAX_RESERVE_PARTICIPANTS
        from datetime import datetime
        
        tournament = TournamentService.get_tournament_by_id(tournament_id)
        
        if not tournament:
            await query.edit_message_text("Турнир не найден")
            return
        
        # Получаем данные об участниках
        counts = ParticipationService.get_participants_count(tournament_id)
        participants = ParticipationService.get_tournament_participants(tournament_id)

        text = f"🏆 {tournament['name']}\n\n"
        text += f"📅 {tournament['date']}\n"
        text += f"📍 {tournament['location']}\n"
        text += f"✅ {tournament['format_info']}\n"
        text += f"💳 {tournament['entry_fee']}\n\n"
        text += f"👥 Участники: {counts['main']}/{MAX_MAIN_PARTICIPANTS} основных\n"
        text += f"📋 Резерв: {counts['reserve']}/{MAX_RESERVE_PARTICIPANTS}\n\n"

        # Разделяем участников на основных и резерв
        main_participants = [p for p in participants if p['position'] <= MAX_MAIN_PARTICIPANTS]
        reserve_participants = [p for p in participants if p['position'] > MAX_MAIN_PARTICIPANTS]

        # Основные участники
        if main_participants:
            text += "👥 УЧАСТНИКИ:\n"
            for participant in main_participants:
                text += f"{participant['status_icon']} {participant['position']}. {participant['name']}\n"
            text += "\n"
        else:
            text += "👥 УЧАСТНИКИ:\nПока никого нет\n\n"

        # Резервные участники
        if reserve_participants:
            text += "📋 РЕЗЕРВ:\n"
            for participant in reserve_participants:
                text += f"{participant['status_icon']} {participant['position']}. {participant['name']}\n"
            text += "\n"
        else:
            text += "📋 РЕЗЕРВ:\nПока никого нет\n\n"

        text += f"📝 ОПИСАНИЕ:\n{tournament['description']}\n\n"

        # Определяем статус кнопки
        user_id = query.from_user.id
        user_participation = ParticipationService.get_user_participation_status(user_id, tournament_id)
        total_available = counts['available_main'] + counts['available_reserve']

        # Показываем таймер если пользователь в pending
        if user_participation and user_participation['status'] == 'pending':
            deadline = datetime.fromisoformat(user_participation['payment_deadline'])
            current_time = datetime.now()
            
            text += f"⏰ ВАША ЗАЯВКА: Оплатите до {deadline.strftime('%H:%M:%S')}\n"
            text += f"📱 Сейчас: {current_time.strftime('%H:%M:%S')}\n"
            
            remaining = deadline - current_time
            if remaining.total_seconds() > 0:
                minutes = int(remaining.total_seconds() // 60)
                seconds = int(remaining.total_seconds() % 60)
                text += f"⏳ Осталось: {minutes} мин {seconds} сек\n\n"
            else:
                text += f"❌ Время истекло\n\n"

        if user_participation:
            if user_participation['status'] == 'confirmed':
                keyboard = [
                    [InlineKeyboardButton("✅ ВЫ ЗАПИСАНЫ", callback_data=f"confirmed_{tournament_id}")],
                    [InlineKeyboardButton("❌ Отменить участие", callback_data=f"leave_{tournament_id}")],
                    [InlineKeyboardButton("← Назад к списку", callback_data="back_to_tournaments")]
                ]
            elif user_participation['status'] == 'pending':
                keyboard = [
                    [InlineKeyboardButton("🟡 ОЖИДАЕТ ОПЛАТЫ", callback_data=f"pending_{tournament_id}")],
                    [InlineKeyboardButton("💳 Оплата Kaspi", url="https://pay.kaspi.kz/pay/g6b21oa4")],
                    [InlineKeyboardButton("❌ Отменить участие", callback_data=f"leave_{tournament_id}")],
                    [InlineKeyboardButton("← Назад к списку", callback_data="back_to_tournaments")]
                ]
            else:
                keyboard = [
                    [InlineKeyboardButton("❌ ОТМЕНИТЬ УЧАСТИЕ", callback_data=f"leave_{tournament_id}")],
                    [InlineKeyboardButton("← Назад к списку", callback_data="back_to_tournaments")]
                ]
        else:
            if total_available > 0:
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
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in cancel_leave_tournament: {e}")
        await query.edit_message_text("Произошла ошибка")

async def handle_pending_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия на кнопку pending статуса"""
    query = update.callback_query
    await query.answer("Дождитесь окончания времени оплаты или одобрения организатора", show_alert=True)

async def handle_confirmed_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия на кнопку confirmed статуса"""
    query = update.callback_query
    await query.answer("Вы уже записаны на турнир!", show_alert=True)