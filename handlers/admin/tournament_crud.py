from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import logging
from config import SEND_NOTIFICATIONS
from states.admin_states import TournamentCreationStates, TournamentEditStates, END
from services.tournament_service import TournamentService
from services.notification_service import NotificationService
from handlers.admin.panel import is_admin, is_super_admin, is_moderator
from utils.admin_keyboards import get_admin_panel_keyboard, get_admin_panel_text
from services.participation_service import ParticipationService
from levels import PLAYER_LEVELS, get_level_name
import asyncio

logger = logging.getLogger(__name__)

async def start_tournament_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать создание турнира"""
    try:
        user_id = update.effective_user.id
        if not is_super_admin(user_id):
            await update.callback_query.answer("Нет прав доступа")
            return END
        if not is_admin(user_id):
            await update.callback_query.answer("Нет прав доступа")
            return END
        
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("👤 Одиночный турнир", callback_data="tournament_type_single")],
            [InlineKeyboardButton("👥 Парный турнир", callback_data="tournament_type_double")],
            [InlineKeyboardButton("❌ Отмена", callback_data="admin_panel_return")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "Создание нового турнира\n\n"
            "Выберите тип турнира:",
            reply_markup=reply_markup
        )
        
        return TournamentCreationStates.WAITING_TYPE
        
    except Exception as e:
        logger.error(f"Error in start_tournament_creation: {e}")
        await update.callback_query.edit_message_text("Произошла ошибка")
        return END

async def handle_tournament_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора типа турнира"""
    try:
        query = update.callback_query
        await query.answer()
        
        tournament_type = query.data.split("_")[2]  # single или double
        context.user_data['tournament_type'] = tournament_type
        
        type_text = "одиночный" if tournament_type == "single" else "парный"
        
        keyboard = [
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_panel_return")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"Создание {type_text} турнира\n\n"
            f"Введите название турнира:",
            reply_markup=reply_markup
        )
        
        return TournamentCreationStates.WAITING_NAME
        
    except Exception as e:
        logger.error(f"Error in handle_tournament_type: {e}")
        await query.edit_message_text("Произошла ошибка")
        return END

async def ask_tournament_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка названия турнира"""
    try:
        name = update.message.text.strip()
        
        keyboard = [
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_panel_return")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if len(name) < 3:
            await update.message.reply_text(
                "Название слишком короткое. Введите название турнира:",
                reply_markup=reply_markup
            )
            return TournamentCreationStates.WAITING_NAME
        
        context.user_data['tournament_name'] = name
        
        await update.message.reply_text(
            f"Название: {name}\n\n"
            "Введите дату и время проведения:\n"
            "Пример: ⏰ 30 и 31 августа, субботу и воскресенье",
            reply_markup=reply_markup
        )
        
        return TournamentCreationStates.WAITING_DATE
        
    except Exception as e:
        logger.error(f"Error in ask_tournament_name: {e}")
        await update.message.reply_text("Произошла ошибка")
        return END

async def ask_tournament_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка даты турнира"""
    try:
        date = update.message.text.strip()
        
        keyboard = [
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_panel_return")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if len(date) < 5:
            await update.message.reply_text(
                "Дата слишком короткая. Введите дату и время:\n"
                "Пример: ⏰ 30 и 31 августа, субботу и воскресенье",
                reply_markup=reply_markup
            )
            return TournamentCreationStates.WAITING_DATE
        
        context.user_data['tournament_date'] = date
        
        await update.message.reply_text(
            f"Дата: {date}\n\n"
            "Введите место проведения:\n"
            "Пример: 📍 ADD Padel Indoor Алматы, Утепова, 2/2",
            reply_markup=reply_markup
        )
        
        return TournamentCreationStates.WAITING_LOCATION
        
    except Exception as e:
        logger.error(f"Error in ask_tournament_date: {e}")
        await update.message.reply_text("Произошла ошибка")
        return END

async def ask_tournament_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка места проведения"""
    try:
        location = update.message.text.strip()
        
        context.user_data['tournament_location'] = location
        
        keyboard = [
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_panel_return")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Место: {location}\n\n"
            "Введите формат турнира:\n"
            "Пример: ✅ Турниры в формате Мексикано и Американо поэтому напарник не требуется.",
            reply_markup=reply_markup
        )
        
        return TournamentCreationStates.WAITING_FORMAT
        
    except Exception as e:
        logger.error(f"Error in ask_tournament_location: {e}")
        await update.message.reply_text("Произошла ошибка")
        return END

async def ask_tournament_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка формата турнира"""
    try:
        format_info = update.message.text.strip()
        
        context.user_data['tournament_format'] = format_info
        
        keyboard = [
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_panel_return")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Формат: {format_info}\n\n"
            "Введите стоимость участия:\n"
            "Пример: 💳 Стоимость 20000₸/чел по факту или (15000₸ если предоплату kaspi pay)",
            reply_markup=reply_markup
        )
        
        return TournamentCreationStates.WAITING_ENTRY_FEE
        
    except Exception as e:
        logger.error(f"Error in ask_tournament_format: {e}")
        await update.message.reply_text("Произошла ошибка")
        return END

async def ask_tournament_entry_fee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка стоимости участия"""
    try:
        entry_fee = update.message.text.strip()
        
        context.user_data['tournament_entry_fee'] = entry_fee
        
        keyboard = [
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_panel_return")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Стоимость: {entry_fee}\n\n"
            "Введите описание турнира (расписание и дополнительную информацию):",
            reply_markup=reply_markup
        )
        
        return TournamentCreationStates.WAITING_DESCRIPTION  # ← Без изменений, идём дальше
        
    except Exception as e:
        logger.error(f"Error in ask_tournament_entry_fee: {e}")
        await update.message.reply_text("Произошла ошибка")
        return END

async def ask_level_restriction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Спросить про ограничения по уровню"""
    try:
        description = update.message.text.strip()
        
        context.user_data['tournament_description'] = description
        
        # Спрашиваем про ограничения
        text = "Установить ограничения по уровню игроков?\n\n"
        text += "🟢 Открытый турнир - могут участвовать игроки любого уровня\n\n"
        text += "🔒 Установить уровни - только игроки определённого диапазона уровней"
        
        keyboard = [
            [InlineKeyboardButton("🟢 Открытый турнир (любой уровень)", callback_data="level_open")],
            [InlineKeyboardButton("🔒 Установить ограничения", callback_data="level_restricted")],
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_panel_return")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        
        return TournamentCreationStates.WAITING_LEVEL_RESTRICTION
        
    except Exception as e:
        logger.error(f"Error in ask_level_restriction: {e}")
        await update.message.reply_text("Произошла ошибка")
        return END

async def handle_level_restriction_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора типа ограничения"""
    try:
        query = update.callback_query
        await query.answer()
        
        choice = query.data  # "level_open" или "level_restricted"
        
        if choice == "level_open":
            # Открытый турнир - сразу создаём
            context.user_data['level_restriction'] = 'open'
            context.user_data['min_level'] = None
            context.user_data['max_level'] = None
            
            # Создаём турнир
            await finish_tournament_creation_with_levels(update, context)
            return END
            
        elif choice == "level_restricted":
            # Устанавливаем ограничения - выбираем минимальный уровень
            context.user_data['level_restriction'] = 'restricted'
            
            text = "Выберите МИНИМАЛЬНЫЙ уровень участников:\n\n"
            
            keyboard = []
            
            # Все уровни из levels.py
            for cat_code, category in PLAYER_LEVELS.items():
                for level_code, level_name in category['levels'].items():
                    keyboard.append([
                        InlineKeyboardButton(
                            f"{level_code} - {level_name}", 
                            callback_data=f"minlevel_{level_code}"
                        )
                    ])
            
            keyboard.append([InlineKeyboardButton("❌ Отменить", callback_data="admin_panel_return")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup)
            
            return TournamentCreationStates.WAITING_MIN_LEVEL
        
    except Exception as e:
        logger.error(f"Error in handle_level_restriction_choice: {e}")
        await query.edit_message_text("Произошла ошибка")
        return END
        
async def handle_min_level_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора минимального уровня"""
    try:
        query = update.callback_query
        await query.answer()
        
        # Получаем выбранный уровень: minlevel_3.5 -> 3.5
        min_level = query.data.replace("minlevel_", "")
        
        context.user_data['min_level'] = min_level
        
        # Теперь выбираем максимальный уровень
        text = f"Минимальный уровень: {min_level} ({get_level_name(min_level)})\n\n"
        text += "Выберите МАКСИМАЛЬНЫЙ уровень участников:\n\n"
        
        keyboard = []
        
        # Показываем только уровни >= минимального
        for cat_code, category in PLAYER_LEVELS.items():
            for level_code, level_name in category['levels'].items():
                if float(level_code) >= float(min_level):
                    keyboard.append([
                        InlineKeyboardButton(
                            f"{level_code} - {level_name}", 
                            callback_data=f"maxlevel_{level_code}"
                        )
                    ])
        
        keyboard.append([InlineKeyboardButton("← Назад", callback_data="level_restricted")])
        keyboard.append([InlineKeyboardButton("❌ Отменить", callback_data="admin_panel_return")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        
        return TournamentCreationStates.WAITING_MAX_LEVEL
        
    except Exception as e:
        logger.error(f"Error in handle_min_level_selection: {e}")
        await query.edit_message_text("Произошла ошибка")
        return END

async def handle_max_level_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора максимального уровня и создание турнира"""
    try:
        query = update.callback_query
        await query.answer()
        
        # Получаем выбранный уровень: maxlevel_4.5 -> 4.5
        max_level = query.data.replace("maxlevel_", "")
        
        context.user_data['max_level'] = max_level
        
        # Создаём турнир
        await finish_tournament_creation_with_levels(update, context)
        
        return END
        
    except Exception as e:
        logger.error(f"Error in handle_max_level_selection: {e}")
        await query.edit_message_text("Произошла ошибка")
        return END

async def finish_tournament_creation_with_levels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершение создания турнира С учётом уровней"""
    try:
        # Получаем все данные
        name = context.user_data['tournament_name']
        date = context.user_data['tournament_date']
        location = context.user_data['tournament_location']
        format_info = context.user_data['tournament_format']
        entry_fee = context.user_data['tournament_entry_fee']
        description = context.user_data['tournament_description']
        created_by = update.effective_user.id if update.effective_user else update.callback_query.from_user.id
        tournament_type = context.user_data.get('tournament_type', 'single')
        
        # НОВОЕ: данные об уровнях
        level_restriction = context.user_data.get('level_restriction', 'open')
        min_level = context.user_data.get('min_level')
        max_level = context.user_data.get('max_level')

        # Создаем турнир (обновляем функцию TournamentService)
        from services.tournament_service import TournamentService
        
        new_tournament_id = TournamentService.create_tournament_with_levels(
            name=name,
            date=date,
            location=location,
            format_info=format_info,
            entry_fee=entry_fee,
            description=description,
            created_by=created_by,
            tournament_type=tournament_type,
            level_restriction=level_restriction,
            min_level=min_level,
            max_level=max_level
        )
        
        if new_tournament_id:
            # Получаем созданный турнир
            new_tournament = TournamentService.get_tournament_by_id(new_tournament_id)
            
            # Автоматически добавляем системных пользователей только для одиночных турниров
            if tournament_type == 'single':
                RESERVE_USERS = [-1000001, -1000002]
                
                for reserve_user_id in RESERVE_USERS:
                    try:
                        ParticipationService.add_participant(reserve_user_id, new_tournament_id)
                        logger.info(f"Reserve slot {reserve_user_id} automatically added to tournament {new_tournament_id}")
                    except Exception as e:
                        logger.error(f"Failed to add reserve slot {reserve_user_id} to tournament: {e}")
            
            keyboard = [
                [InlineKeyboardButton("Создать еще турнир", callback_data="create_tournament")],
                [InlineKeyboardButton("Админ панель", callback_data="admin_panel_return")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            type_text = "Одиночный" if tournament_type == 'single' else "Парный"
            
            # Формируем текст с информацией об уровнях
            success_text = (
                f"{type_text} турнир создан!\n\n"
                f"Название: {name}\n"
                f"Дата: {date}\n"
                f"Место: {location}\n"
                f"Формат: {format_info}\n"
                f"Стоимость: {entry_fee}\n"
            )
            
            # Добавляем информацию об ограничениях
            if level_restriction == 'open':
                success_text += f"⭐ Уровень: Открытый турнир (любой уровень)\n\n"
            else:
                success_text += (
                    f"⭐ Уровень участников: {min_level} - {max_level}\n"
                    f"   ({get_level_name(min_level)} - {get_level_name(max_level)})\n\n"
                )
            
            success_text += f"Описание: {description}\n\n"
            
            # ============================================
            # ИЗМЕНЕНИЕ: Запускаем рассылку В ФОНЕ
            # ============================================
            if SEND_NOTIFICATIONS:
                success_text += "🚀 Уведомления отправляются в фоновом режиме..."
                
                # Запускаем рассылку в фоне, не дожидаясь её завершения
                asyncio.create_task(
                    NotificationService.notify_new_tournament(
                        context.application, new_tournament
                    )
                )
            
            # Отправляем сообщение СРАЗУ, не дожидаясь рассылки
            if update.callback_query:
                await update.callback_query.edit_message_text(success_text, reply_markup=reply_markup)
            else:
                await update.message.reply_text(success_text, reply_markup=reply_markup)
        else:
            error_text = "Ошибка при создании турнира"
            if update.callback_query:
                await update.callback_query.edit_message_text(error_text)
            else:
                await update.message.reply_text(error_text)
        
        context.user_data.clear()
        
    except Exception as e:
        logger.error(f"Error in finish_tournament_creation_with_levels: {e}")
        error_text = "Произошла ошибка при создании турнира"
        if update.callback_query:
            await update.callback_query.edit_message_text(error_text)
        else:
            await update.message.reply_text(error_text)

async def cancel_tournament_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена создания турнира"""
    await update.message.reply_text("Создание турнира отменено")
    context.user_data.clear()
    return END

async def cancel_tournament_creation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена создания турнира через callback"""
    try:
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(get_admin_panel_text(), reply_markup=get_admin_panel_keyboard())
        
        context.user_data.clear()
        return END
        
    except Exception as e:
        logger.error(f"Error in cancel_tournament_creation_callback: {e}")
        return END

async def return_to_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в админ панель - ПОКАЗЫВАЕТ ПРАВИЛЬНОЕ МЕНЮ"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # Определяем уровень доступа и показываем соответствующее меню
        if is_super_admin(user_id):
            from utils.admin_keyboards import get_admin_panel_keyboard, get_admin_panel_text
            reply_markup = get_admin_panel_keyboard()
            text = get_admin_panel_text()
        elif is_moderator(user_id):
            from utils.admin_keyboards import get_moderator_panel_keyboard, get_moderator_panel_text
            reply_markup = get_moderator_panel_keyboard()
            text = get_moderator_panel_text()
        else:
            await query.edit_message_text("Нет прав доступа")
            return
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in return_to_admin_panel: {e}")
        await query.edit_message_text("Произошла ошибка")

async def start_tournament_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать редактирование турнира"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if not is_super_admin(user_id):
            await query.edit_message_text("Нет прав доступа. Эта функция доступна только главному администратору.")
            return END
        if not is_admin(user_id):
            await query.edit_message_text("Нет прав доступа")
            return END
        
        tournaments = TournamentService.get_all_tournaments()
        
        if not tournaments:
            keyboard = [[InlineKeyboardButton("← Назад", callback_data="admin_panel_return")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "Нет активных турниров для редактирования",
                reply_markup=reply_markup
            )
            return END
        
        text = "Выберите турнир для редактирования:\n\n"
        keyboard = []
        
        for tournament in tournaments:
            text += f"🏆 {tournament['name']}\n"
            text += f"📅 {tournament['date']}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"{tournament['name']}", 
                    callback_data=f"edit_tournament_{tournament['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("← Назад", callback_data="admin_panel_return")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return TournamentEditStates.SELECTING_TOURNAMENT
        
    except Exception as e:
        logger.error(f"Error in start_tournament_edit: {e}")
        await query.edit_message_text("Произошла ошибка")
        return END

async def select_tournament_for_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор турнира для редактирования"""
    try:
        query = update.callback_query
        await query.answer()
        
        tournament_id = int(query.data.split("_")[2])
        tournament = TournamentService.get_tournament_by_id(tournament_id)
        
        if not tournament:
            await query.edit_message_text("Турнир не найден")
            return END
        
        context.user_data['editing_tournament_id'] = tournament_id
        context.user_data['tournament_data'] = tournament
        
        text = f"Редактирование турнира: {tournament['name']}\n\n"
        text += "Что хотите изменить?\n\n"
        text += f"📝 Название: {tournament['name']}\n"
        text += f"📅 Дата: {tournament['date']}\n"
        text += f"📍 Место: {tournament['location']}\n"
        text += f"✅ Формат: {tournament['format_info']}\n"
        text += f"💳 Стоимость: {tournament['entry_fee']}\n"
        text += f"📋 Описание: {tournament['description'][:50]}...\n"
        
        keyboard = [
            [InlineKeyboardButton("📝 Изменить название", callback_data="edit_field_name")],
            [InlineKeyboardButton("📅 Изменить дату", callback_data="edit_field_date")],
            [InlineKeyboardButton("📍 Изменить место", callback_data="edit_field_location")],
            [InlineKeyboardButton("✅ Изменить формат", callback_data="edit_field_format")],
            [InlineKeyboardButton("💳 Изменить стоимость", callback_data="edit_field_entry_fee")],
            [InlineKeyboardButton("📋 Изменить описание", callback_data="edit_field_description")],
            [InlineKeyboardButton("💾 Завершить редактирование", callback_data="finish_edit")],
            [InlineKeyboardButton("❌ Отмена", callback_data="admin_panel_return")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return TournamentEditStates.SELECTING_TOURNAMENT
        
    except Exception as e:
        logger.error(f"Error in select_tournament_for_edit: {e}")
        await query.edit_message_text("Произошла ошибка")
        return END
        
async def edit_tournament_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка редактирования конкретного поля"""
    try:
        query = update.callback_query
        await query.answer()
        
        # ИСПРАВЛЕНИЕ: получаем все после "edit_field_"
        field = query.data.replace("edit_field_", "")  # Вместо split("_")[2]
        logger.info(f"Editing field: {field}")
        
        field_names = {
            'name': ('название', 'Новый турнир по паддлу'),
            'date': ('дату и время', '30 и 31 августа, субботу и воскресенье'),
            'location': ('место проведения', 'ADD Padel Indoor Алматы'),
            'format': ('формат турнира', 'Мексикано и Американо'),
            'entry_fee': ('стоимость', '20000₸/чел'),  # Теперь это будет работать
            'description': ('описание', 'Подробное описание турнира')
        }
        
        field_name, example = field_names.get(field, ('поле', 'значение'))
        
        keyboard = [
            [InlineKeyboardButton("❌ Отмена редактирования", callback_data="cancel_field_edit")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"Введите новое значение для поля '{field_name}':\n\n"
            f"Пример: {example}\n\n"
            f"Или введите '-' чтобы оставить без изменений",
            reply_markup=reply_markup
        )
        
        context.user_data['editing_field'] = field
        
        # Возвращаем соответствующее состояние
        states_map = {
            'name': TournamentEditStates.EDITING_NAME,
            'date': TournamentEditStates.EDITING_DATE,
            'location': TournamentEditStates.EDITING_LOCATION,
            'format': TournamentEditStates.EDITING_FORMAT,
            'entry_fee': TournamentEditStates.EDITING_ENTRY_FEE,
            'description': TournamentEditStates.EDITING_DESCRIPTION
        }
        
        next_state = states_map.get(field, END)
        logger.info(f"Returning state: {next_state}")
        
        return next_state
        
    except Exception as e:
        logger.error(f"Error in edit_tournament_field: {e}")
        return END
        
async def handle_field_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода нового значения поля"""
    try:
        new_value = update.message.text.strip()
        field = context.user_data.get('editing_field')
        logger.info(f"Editing field: {field}, new value: {new_value}")  # ДОБАВИТЬ
        tournament_id = context.user_data.get('editing_tournament_id')
        
        # Если введен '-', оставляем поле без изменений
        if new_value == '-':
            keyboard = [
                [InlineKeyboardButton("← К редактированию", callback_data=f"edit_tournament_{tournament_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "Поле оставлено без изменений",
                reply_markup=reply_markup
            )
            return TournamentEditStates.SELECTING_TOURNAMENT
        
        # Сохраняем новое значение
        if 'updated_fields' not in context.user_data:
            context.user_data['updated_fields'] = {}
        
        context.user_data['updated_fields'][field] = new_value
        logger.info(f"Updated fields now: {context.user_data['updated_fields']}")  # ДОБАВИТЬ
        field_names = {
            'name': 'название',
            'date': 'дата',
            'location': 'место',
            'format': 'формат',
            'entry_fee': 'стоимость',
            'description': 'описание'
        }
        
        field_name = field_names.get(field, 'поле')
        
        keyboard = [
            [InlineKeyboardButton("← Продолжить редактирование", callback_data=f"edit_tournament_{tournament_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ {field_name.capitalize()} изменено на: {new_value}",
            reply_markup=reply_markup
        )
        
        return TournamentEditStates.SELECTING_TOURNAMENT
        
    except Exception as e:
        logger.error(f"Error in handle_field_edit: {e}")
        await update.message.reply_text("Произошла ошибка")
        return END

async def finish_tournament_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершение редактирования турнира"""
    try:
        query = update.callback_query
        await query.answer()
        
        tournament_id = context.user_data.get('editing_tournament_id')
        updated_fields = context.user_data.get('updated_fields', {})
        
        logger.info(f"Finishing edit for tournament {tournament_id} with fields: {updated_fields}")
        
        if not updated_fields:
            await query.edit_message_text(
                "Изменения не были внесены",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("← Админ панель", callback_data="admin_panel_return")
                ]])
            )
            context.user_data.clear()
            return END
        
        # Применяем изменения
        success = TournamentService.update_tournament(tournament_id, updated_fields)
        logger.info(f"Update result: {success}")
        
        if success:
            changes_text = "\n".join([f"• {field}: {value}" for field, value in updated_fields.items()])
            
            keyboard = [
                [InlineKeyboardButton("✏️ Редактировать еще", callback_data="edit_tournament")],
                [InlineKeyboardButton("← Админ панель", callback_data="admin_panel_return")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ Турнир успешно обновлен!\n\nИзменения:\n{changes_text}",
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text("Ошибка при сохранении изменений")
        
        context.user_data.clear()
        return END
        
    except Exception as e:
        logger.error(f"Error in finish_tournament_edit: {e}")
        await query.edit_message_text("Произошла ошибка")
        return END

async def cancel_field_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена редактирования поля"""
    try:
        query = update.callback_query
        await query.answer()
        
        tournament_id = context.user_data.get('editing_tournament_id')
        
        await query.edit_message_text(
            "Редактирование поля отменено",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("← К редактированию", callback_data=f"edit_tournament_{tournament_id}")
            ]])
        )
        
        return TournamentEditStates.SELECTING_TOURNAMENT
        
    except Exception as e:
        logger.error(f"Error in cancel_field_edit: {e}")
        return END 