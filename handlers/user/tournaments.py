from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import logging
from services.tournament_service import TournamentService
from config import MAX_MAIN_PARTICIPANTS, MAX_RESERVE_PARTICIPANTS
from services.participation_service import ParticipationService
from datetime import datetime
from levels import get_level_name, check_level_in_range
from utils.keyboards import get_main_menu_keyboard  # ← ДОБАВИТЬ ЭТУ СТРОКУ!

logger = logging.getLogger(__name__)

async def show_tournaments_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список турниров в виде кнопок"""
    try:
        tournaments = TournamentService.get_all_tournaments()
        
        if not tournaments:
            await update.message.reply_text(
                "Нет активных турниров.\n"
                "Следите за объявлениями!"
            )
            return
        
        text = "🏆 Доступные турниры:\n\n"
        text += "Выберите турнир для получения подробной информации:"
        
        keyboard = []
        
        # Создаем кнопку для каждого турнира
        for tournament in tournaments:
            # Получаем краткую информацию для кнопки
            counts = ParticipationService.get_participants_count(tournament['id'])
            available_spots = counts['available_main'] + counts['available_reserve']
            
            # Формируем текст кнопки с индикаторами
            button_text = f"🏆 {tournament['name']}"
            
            # Добавляем индикатор заполненности
            if available_spots == 0:
                button_text += " 🔴"  # Мест нет
            elif counts['available_main'] == 0:
                button_text += " 🟡"  # Только резерв
            else:
                button_text += " 🟢"  # Есть основные места
            
            keyboard.append([
                InlineKeyboardButton(
                    button_text, 
                    callback_data=f"tournament_{tournament['id']}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in show_tournaments_list: {e}")
        await update.message.reply_text("Произошла ошибка при получении турниров")

async def show_tournament_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать детали турнира (теперь с полной информацией)"""
    try:
        query = update.callback_query
        await query.answer()
        
        tournament_id = int(query.data.split("_")[1])
        tournament = TournamentService.get_tournament_by_id(tournament_id)
        
        if not tournament:
            await query.edit_message_text("Турнир не найден")
            return
        if tournament.get('tournament_type') == 'double':
            await show_pair_tournament_details(query, tournament_id, tournament)
            return
        # Получаем данные об участниках
        from services.participation_service import ParticipationService
        counts = ParticipationService.get_participants_count(tournament_id)
        participants = ParticipationService.get_tournament_participants(tournament_id)

        text = f"🏆 {tournament['name']}\n\n"
        text += f"📅 {tournament['date']}\n"
        text += f"📍 {tournament['location']}\n"
        text += f"✅ {tournament['format_info']}\n"
        text += f"💳 {tournament['entry_fee']}\n\n"
        text += f"👥 Участники: {counts['main']}/{MAX_MAIN_PARTICIPANTS} основных\n"
        text += f"📋 Резерв: {counts['reserve']}/{MAX_RESERVE_PARTICIPANTS}\n\n"
        
        if tournament.get('level_restriction') == 'restricted' and tournament.get('min_level') and tournament.get('max_level'):
            min_level = tournament['min_level']
            max_level = tournament['max_level']
            min_name = get_level_name(min_level)
            max_name = get_level_name(max_level)
            
            text += f"⭐ Уровень участников: {min_level} - {max_level}\n"
            text += f"   ({min_name} - {max_name})\n\n"
        elif tournament.get('level_restriction') == 'open':
            text += f"⭐ Открытый турнир (любой уровень)\n\n"

        text += f"👥 Участники: {counts['main']}/{MAX_MAIN_PARTICIPANTS} основных\n"
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

        # Определяем статус кнопки и показываем таймер для pending
        user_id = query.from_user.id
        user_participation = ParticipationService.get_user_participation_status(user_id, tournament_id)
        total_available = counts['available_main'] + counts['available_reserve']

        # Показываем таймер если пользователь в pending
        if user_participation and user_participation['status'] == 'pending':
            from datetime import datetime
            deadline = datetime.fromisoformat(user_participation['payment_deadline'])
            current_time = datetime.now()
            
            text += f"⏰ ВАША ЗАЯВКА: Оплатите до {deadline.strftime('%H:%M:%S')}\n"
            text += f"📱 Сейчас: {current_time.strftime('%H:%M:%S')}\n"
            
            # Считаем оставшееся время
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
            # Логика для незарегистрированных пользователей
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
        logger.error(f"Error in show_tournament_details: {e}")
        await query.edit_message_text("Произошла ошибка")

async def back_to_tournaments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться к списку турниров (теперь показывает только кнопки)"""
    try:
        query = update.callback_query
        await query.answer()
        
        tournaments = TournamentService.get_all_tournaments()
        
        if not tournaments:
            await query.edit_message_text(
                "Нет активных турниров.\n"
                "Следите за объявлениями!"
            )
            return
        
        text = "🏆 Доступные турниры:\n\n"
        text += "Выберите турнир для получения подробной информации:"
        
        keyboard = []
        
        for tournament in tournaments:
            # Получаем краткую информацию для кнопки
            counts = ParticipationService.get_participants_count(tournament['id'])
            available_spots = counts['available_main'] + counts['available_reserve']
            
            # Формируем текст кнопки с индикаторами
            button_text = f"🏆 {tournament['name']}"
            
            # Добавляем индикатор заполненности
            if available_spots == 0:
                button_text += " 🔴"  # Мест нет
            elif counts['available_main'] == 0:
                button_text += " 🟡"  # Только резерв
            else:
                button_text += " 🟢"  # Есть основные места
            
            keyboard.append([
                InlineKeyboardButton(
                    button_text, 
                    callback_data=f"tournament_{tournament['id']}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in back_to_tournaments: {e}")
        await query.edit_message_text("Произошла ошибка")
        
async def show_tournament_details_direct(update: Update, context: ContextTypes.DEFAULT_TYPE, tournament_id: int):
    """Показать детали турнира напрямую (для deep links)"""
    try:
        tournament = TournamentService.get_tournament_by_id(tournament_id)
        
        if not tournament:
            await update.message.reply_text(
                "Турнир не найден или уже завершен.",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Получаем данные об участниках
        from services.participation_service import ParticipationService
        counts = ParticipationService.get_participants_count(tournament_id)
        participants = ParticipationService.get_tournament_participants(tournament_id)

        text = f"🏆 {tournament['name']}\n\n"
        text += f"📅 {tournament['date']}\n"
        text += f"📍 {tournament['location']}\n"
        text += f"✅ {tournament['format_info']}\n"
        text += f"💳 {tournament['entry_fee']}\n\n"
        text += f"👥 Участники: {counts['main']}/{MAX_MAIN_PARTICIPANTS} основных\n"
        text += f"📋 Резерв: {counts['reserve']}/{MAX_RESERVE_PARTICIPANTS}\n\n"
        
        if tournament.get('level_restriction') == 'restricted' and tournament.get('min_level') and tournament.get('max_level'):
            min_level = tournament['min_level']
            max_level = tournament['max_level']
            min_name = get_level_name(min_level)
            max_name = get_level_name(max_level)
            
            text += f"⭐ Уровень участников: {min_level} - {max_level}\n"
            text += f"   ({min_name} - {max_name})\n\n"
        elif tournament.get('level_restriction') == 'open':
            text += f"⭐ Открытый турнир (любой уровень)\n\n"

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
        user_id = update.effective_user.id
        user_participation = ParticipationService.get_user_participation_status(user_id, tournament_id)
        total_available = counts['available_main'] + counts['available_reserve']

        if user_participation:
            if user_participation['status'] == 'confirmed':
                keyboard = [
                    [InlineKeyboardButton("✅ ВЫ ЗАПИСАНЫ", callback_data=f"confirmed_{tournament_id}")],
                    [InlineKeyboardButton("❌ Отменить участие", callback_data=f"leave_{tournament_id}")],
                ]
            elif user_participation['status'] == 'pending':
                keyboard = [
                    [InlineKeyboardButton("🟡 ОЖИДАЕТ ОПЛАТЫ", callback_data=f"pending_{tournament_id}")],
                    [InlineKeyboardButton("💳 Оплата Kaspi", url="https://pay.kaspi.kz/pay/g6b21oa4")],
                    [InlineKeyboardButton("❌ Отменить участие", callback_data=f"leave_{tournament_id}")],
                ]
            else:
                keyboard = [
                    [InlineKeyboardButton("❌ ОТМЕНИТЬ УЧАСТИЕ", callback_data=f"leave_{tournament_id}")],
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
            ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        
        # Показываем главное меню
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=get_main_menu_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in show_tournament_details_direct: {e}")
        await update.message.reply_text("Произошла ошибка")
        
async def show_pair_tournament_details(query, tournament_id: int, tournament: dict):
    """Показать детали ПАРНОГО турнира"""
    try:
        from services.pair_service import PairService
        from config import MAX_PAIR_SLOTS, MAX_PAIR_RESERVE
        from levels import get_level_name
        
        # Получаем данные о парах
        counts = PairService.get_pairs_count(tournament_id)
        pairs = PairService.get_tournament_pairs(tournament_id)

        text = f"👥 {tournament['name']} (ПАРНЫЙ)\n\n"
        text += f"📅 {tournament['date']}\n"
        text += f"📍 {tournament['location']}\n"
        text += f"✅ {tournament['format_info']}\n"
        text += f"💳 {tournament['entry_fee']}\n\n"
        text += f"👥 Пары: {counts['main']}/{MAX_PAIR_SLOTS} основных\n"
        text += f"📋 Резерв: {counts['reserve']}/{MAX_PAIR_RESERVE}\n\n"
        
        # Информация об уровнях
        if tournament.get('level_restriction') == 'restricted' and tournament.get('min_level') and tournament.get('max_level'):
            min_level = tournament['min_level']
            max_level = tournament['max_level']
            min_name = get_level_name(min_level)
            max_name = get_level_name(max_level)
            
            text += f"⭐ Уровень участников: {min_level} - {max_level}\n"
            text += f"   ({min_name} - {max_name})\n\n"
        elif tournament.get('level_restriction') == 'open':
            text += f"⭐ Открытый турнир (любой уровень)\n\n"

        # Разделяем пары на основные и резерв
        main_pairs = [p for p in pairs if p['pair_number'] <= MAX_PAIR_SLOTS]
        reserve_pairs = [p for p in pairs if p['pair_number'] > MAX_PAIR_SLOTS]

        # Основные пары
        if main_pairs:
            text += "👥 ОСНОВНЫЕ ПАРЫ:\n"
            for pair in main_pairs:
                text += f"{pair['status_icon']} Пара {pair['pair_number']}: {pair['player1_name']} / {pair['player2_name']}\n"
            text += "\n"
        else:
            text += "👥 ОСНОВНЫЕ ПАРЫ:\nПока нет пар\n\n"

        # Резервные пары
        if reserve_pairs:
            text += "📋 РЕЗЕРВНЫЕ ПАРЫ:\n"
            for pair in reserve_pairs:
                text += f"{pair['status_icon']} Пара {pair['pair_number']}: {pair['player1_name']} / {pair['player2_name']}\n"
            text += "\n"
        else:
            text += "📋 РЕЗЕРВНЫЕ ПАРЫ:\nПока нет пар\n\n"

        text += f"📝 ОПИСАНИЕ:\n{tournament['description']}\n\n"

        # Определяем статус кнопки
        user_id = query.from_user.id
        user_pair = PairService.get_user_pair(user_id, tournament_id)
        total_available = counts['available_main'] + counts['available_reserve']

        # Показываем таймер если пользователь в pending
        if user_pair and user_pair['status'] == 'pending':
            from datetime import datetime
            deadline = datetime.fromisoformat(user_pair['payment_deadline'])
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

        # Формируем кнопки
        if user_pair:
            if user_pair['status'] == 'confirmed':
                keyboard = [
                    [InlineKeyboardButton("✅ ВЫ ЗАПИСАНЫ", callback_data=f"confirmed_pair_{tournament_id}")],
                    [InlineKeyboardButton("❌ Отменить участие", callback_data=f"leave_pair_{tournament_id}")],
                    [InlineKeyboardButton("← Назад к списку", callback_data="back_to_tournaments")]
                ]
            elif user_pair['status'] == 'pending':
                keyboard = [
                    [InlineKeyboardButton("🟡 ОЖИДАЕТ ОПЛАТЫ", callback_data=f"pending_pair_{tournament_id}")],
                    [InlineKeyboardButton("💳 Оплата Kaspi", url="https://pay.kaspi.kz/pay/g6b21oa4")],
                    [InlineKeyboardButton("❌ Отменить участие", callback_data=f"leave_pair_{tournament_id}")],
                    [InlineKeyboardButton("← Назад к списку", callback_data="back_to_tournaments")]
                ]
            else:
                keyboard = [
                    [InlineKeyboardButton("❌ ОТМЕНИТЬ УЧАСТИЕ", callback_data=f"leave_pair_{tournament_id}")],
                    [InlineKeyboardButton("← Назад к списку", callback_data="back_to_tournaments")]
                ]
        else:
            if total_available > 0:
                if counts['available_main'] > 0:
                    button_text = "🟢 УЧАСТВОВАТЬ В ТУРНИРЕ"
                else:
                    button_text = "🟡 УЧАСТВОВАТЬ (в резерв)"
                button_callback = f"join_pair_{tournament_id}"
            else:
                button_text = "🔴 МЕСТ НЕТ"
                button_callback = f"no_slots_pair_{tournament_id}"
            
            keyboard = [
                [InlineKeyboardButton(button_text, callback_data=button_callback)],
                [InlineKeyboardButton("← Назад к списку", callback_data="back_to_tournaments")]
            ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in show_pair_tournament_details: {e}")
        await query.edit_message_text("Произошла ошибка")


async def handle_confirmed_pair_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия на кнопку confirmed пары"""
    query = update.callback_query
    await query.answer("Вы уже записаны на турнир в паре!", show_alert=True)


async def handle_pending_pair_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия на кнопку pending пары"""
    query = update.callback_query
    await query.answer("Дождитесь окончания времени оплаты или одобрения организатора", show_alert=True)