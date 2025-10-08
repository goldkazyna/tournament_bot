from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import logging
from services.tournament_service import TournamentService
from config import MAX_MAIN_PARTICIPANTS, MAX_RESERVE_PARTICIPANTS
from services.participation_service import ParticipationService
from datetime import datetime

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