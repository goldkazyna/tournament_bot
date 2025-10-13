from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import logging
from services.user_service import UserService
from handlers.admin.panel import is_admin, is_super_admin
from states.admin_states import UserEditStates, END
from levels import PLAYER_LEVELS, get_level_name, get_category_by_level, format_level_display

logger = logging.getLogger(__name__)

# ========================================
# НАЧАЛО РЕДАКТИРОВАНИЯ ПОЛЬЗОВАТЕЛЯ
# ========================================

async def start_user_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса редактирования пользователя - запрос Telegram ID"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if not is_super_admin(user_id):
            await query.edit_message_text("Нет прав доступа. Эта функция доступна только главному администратору.")
            return END
        
        keyboard = [
            [InlineKeyboardButton("❌ Отмена", callback_data="admin_panel_return")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "👤 Редактирование пользователя\n\n"
            "Введите Telegram ID пользователя:\n\n"
            "Например: 123456789\n\n"
            "💡 ID можно найти в таблице экспорта пользователей",
            reply_markup=reply_markup
        )
        
        return UserEditStates.WAITING_TELEGRAM_ID
        
    except Exception as e:
        logger.error(f"Error in start_user_edit: {e}")
        await query.edit_message_text("Произошла ошибка")
        return END

# ========================================
# ПОИСК ПОЛЬЗОВАТЕЛЯ ПО ID
# ========================================

async def find_user_by_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поиск пользователя по введённому Telegram ID"""
    try:
        telegram_id_str = update.message.text.strip()
        
        # Проверяем, что введено число
        if not telegram_id_str.isdigit():
            keyboard = [
                [InlineKeyboardButton("❌ Отмена", callback_data="admin_panel_return")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "❌ Ошибка: введите корректный Telegram ID (только цифры)\n\n"
                "Попробуйте ещё раз:",
                reply_markup=reply_markup
            )
            return UserEditStates.WAITING_TELEGRAM_ID
        
        telegram_id = int(telegram_id_str)
        
        # Ищем пользователя
        user = UserService.search_user_by_id(telegram_id)
        
        if not user:
            keyboard = [
                [InlineKeyboardButton("🔄 Попробовать снова", callback_data="edit_user")],
                [InlineKeyboardButton("❌ Отмена", callback_data="admin_panel_return")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"❌ Пользователь с ID {telegram_id} не найден\n\n"
                "Проверьте правильность ID и попробуйте снова",
                reply_markup=reply_markup
            )
            return END
        
        # Сохраняем данные в контекст
        context.user_data['editing_user_id'] = telegram_id
        context.user_data['editing_user_data'] = user
        
        # Показываем карточку пользователя
        await show_user_card(update, context)
        
        return UserEditStates.SHOWING_USER_CARD
        
    except Exception as e:
        logger.error(f"Error in find_user_by_id: {e}")
        await update.message.reply_text("Произошла ошибка при поиске пользователя")
        return END

# ========================================
# ПОКАЗ КАРТОЧКИ ПОЛЬЗОВАТЕЛЯ
# ========================================

async def show_user_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать карточку пользователя с кнопками редактирования"""
    try:
        user = context.user_data.get('editing_user_data')
        
        if not user:
            await update.message.reply_text("Ошибка: данные пользователя не найдены")
            return END
        
        # Формируем текст карточки
        text = "👤 Карточка пользователя\n\n"
        text += f"📝 ФИО: {user['full_name']}\n"
        text += f"📱 Телефон: {user['phone_number']}\n"
        text += f"🆔 Telegram ID: {user['telegram_id']}\n"
        
        # Форматируем дату регистрации
        if user['created_at']:
            from datetime import datetime
            try:
                created_date = datetime.fromisoformat(user['created_at'])
                text += f"📅 Регистрация: {created_date.strftime('%d.%m.%Y')}\n\n"
            except:
                text += f"📅 Регистрация: {user['created_at'][:10]}\n\n"
        else:
            text += f"📅 Регистрация: не указано\n\n"
        
        # Добавляем информацию об уровне
        if user['player_level']:
            level_display = format_level_display(user['player_level'])
            text += f"{level_display}\n"
            
            # Форматируем дату обновления уровня
            if user['player_level_updated_at']:
                from datetime import datetime
                try:
                    updated_date = datetime.fromisoformat(user['player_level_updated_at'])
                    text += f"🕒 Обновлён: {updated_date.strftime('%d.%m.%Y %H:%M')}\n"
                except:
                    text += f"🕒 Обновлён: {user['player_level_updated_at'][:16]}\n"
        else:
            text += "⭐ Уровень: Не установлен\n"
        
        # Кнопки действий
        keyboard = [
            [InlineKeyboardButton("✏️ Изменить ФИО", callback_data="edit_user_name")],
            [InlineKeyboardButton("⭐ Изменить уровень", callback_data="edit_user_level")],
            [InlineKeyboardButton("🔄 Найти другого пользователя", callback_data="edit_user")],
            [InlineKeyboardButton("← Админ панель", callback_data="admin_panel_return")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in show_user_card: {e}")
        await update.message.reply_text("Произошла ошибка")

# ========================================
# РЕДАКТИРОВАНИЕ ФИО
# ========================================

async def start_edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать редактирование ФИО"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = context.user_data.get('editing_user_data')
        
        keyboard = [
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_user_edit")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✏️ Редактирование ФИО\n\n"
            f"Текущее значение: {user['full_name']}\n\n"
            f"Введите новое ФИО:",
            reply_markup=reply_markup
        )
        
        return UserEditStates.EDITING_NAME
        
    except Exception as e:
        logger.error(f"Error in start_edit_name: {e}")
        await query.edit_message_text("Произошла ошибка")
        return END

async def handle_new_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нового ФИО"""
    try:
        new_name = update.message.text.strip()
        
        if len(new_name) < 2:
            await update.message.reply_text(
                "❌ Слишком короткое имя. Введите корректное ФИО:"
            )
            return UserEditStates.EDITING_NAME
        
        telegram_id = context.user_data.get('editing_user_id')
        old_name = context.user_data['editing_user_data']['full_name']
        
        # Сохраняем в БД
        success = UserService.update_user_name(telegram_id, new_name)
        
        if success:
            # Обновляем данные в контексте
            context.user_data['editing_user_data']['full_name'] = new_name
            
            keyboard = [
                [InlineKeyboardButton("← К карточке пользователя", callback_data="show_user_card_return")],
                [InlineKeyboardButton("🛠️ Админ панель", callback_data="admin_panel_return")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ ФИО успешно изменено!\n\n"
                f"Было: {old_name}\n"
                f"Стало: {new_name}",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("❌ Ошибка при сохранении")
        
        return UserEditStates.SHOWING_USER_CARD  # ← ИЗМЕНИЛИ! Было END
        
    except Exception as e:
        logger.error(f"Error in handle_new_name: {e}")
        await update.message.reply_text("Произошла ошибка")
        return END

# ========================================
# РЕДАКТИРОВАНИЕ УРОВНЯ - ВЫБОР КАТЕГОРИИ
# ========================================

async def start_edit_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать редактирование уровня - выбор категории"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = context.user_data.get('editing_user_data')
        
        text = f"⭐ Редактирование уровня\n\n"
        text += f"Пользователь: {user['full_name']}\n"
        
        if user['player_level']:
            text += f"Текущий уровень: {format_level_display(user['player_level'])}\n"
        else:
            text += f"Текущий уровень: Не установлен\n"
        
        text += f"\nВыберите категорию:"
        
        # Кнопки категорий
        keyboard = []
        
        for cat_code, category in PLAYER_LEVELS.items():
            keyboard.append([
                InlineKeyboardButton(
                    f"{category['emoji']} {category['name']}", 
                    callback_data=f"select_category_{cat_code}"
                )
            ])
        
        # Кнопка сброса уровня (если уровень установлен)
        if user['player_level']:
            keyboard.append([
                InlineKeyboardButton("🗑️ Сбросить уровень", callback_data="reset_level")
            ])
        
        keyboard.append([
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_user_edit")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        
        return UserEditStates.SELECTING_CATEGORY
        
    except Exception as e:
        logger.error(f"Error in start_edit_level: {e}")
        await query.edit_message_text("Произошла ошибка")
        return END

# ========================================
# ВЫБОР КОНКРЕТНОГО УРОВНЯ
# ========================================

async def select_level_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать уровни выбранной категории"""
    try:
        query = update.callback_query
        await query.answer()
        
        # Получаем код категории из callback_data
        category_code = query.data.split("_")[2]  # select_category_B -> B
        
        category = PLAYER_LEVELS[category_code]
        user = context.user_data.get('editing_user_data')
        
        text = f"{category['emoji']} {category['name']}\n\n"
        text += f"Пользователь: {user['full_name']}\n\n"
        text += f"Выберите уровень:"
        
        # Кнопки уровней
        keyboard = []
        
        for level_code, level_name in category['levels'].items():
            keyboard.append([
                InlineKeyboardButton(
                    f"{level_code} - {level_name}", 
                    callback_data=f"set_level_{level_code}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("← Назад к категориям", callback_data="edit_user_level")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        
        return UserEditStates.SELECTING_LEVEL
        
    except Exception as e:
        logger.error(f"Error in select_level_category: {e}")
        await query.edit_message_text("Произошла ошибка")
        return END

# ========================================
# СОХРАНЕНИЕ ВЫБРАННОГО УРОВНЯ
# ========================================

async def save_selected_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранить выбранный уровень"""
    try:
        query = update.callback_query
        await query.answer()
        
        # Получаем код уровня из callback_data
        level_code = query.data.replace("set_level_", "")
        
        telegram_id = context.user_data.get('editing_user_id')
        admin_id = query.from_user.id
        user = context.user_data.get('editing_user_data')
        
        # Сохраняем в БД
        success = UserService.set_player_level(telegram_id, level_code, admin_id)
        
        if success:
            # Обновляем данные в контексте
            context.user_data['editing_user_data']['player_level'] = level_code
            
            level_name = get_level_name(level_code)
            category = get_category_by_level(level_code)
            
            keyboard = [
                [InlineKeyboardButton("← К карточке пользователя", callback_data="show_user_card_return")],
                [InlineKeyboardButton("✏️ Редактировать ещё", callback_data="edit_user")],
                [InlineKeyboardButton("🛠️ Админ панель", callback_data="admin_panel_return")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ Уровень успешно изменён!\n\n"
                f"Пользователь: {user['full_name']}\n"
                f"Новый уровень: {level_code} ({level_name})\n"
                f"Категория: {category}\n"
                f"Изменил: {query.from_user.first_name}",
                reply_markup=reply_markup
            )
            
            # Отправляем уведомление пользователю
            try:
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=f"⭐ Ваш уровень игры обновлён!\n\n"
                         f"Новый уровень: {level_code} ({level_name})\n"
                         f"Категория: {category}"
                )
            except Exception as e:
                logger.error(f"Failed to send level update notification to {telegram_id}: {e}")
        else:
            await query.edit_message_text("❌ Ошибка при сохранении уровня")
        
        return UserEditStates.SHOWING_USER_CARD  # ← ИЗМЕНИЛИ! Было END
        
    except Exception as e:
        logger.error(f"Error in save_selected_level: {e}")
        await query.edit_message_text("Произошла ошибка")
        return END

# ========================================
# СБРОС УРОВНЯ
# ========================================

async def reset_user_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сбросить уровень пользователя"""
    try:
        query = update.callback_query
        await query.answer()
        
        telegram_id = context.user_data.get('editing_user_id')
        admin_id = query.from_user.id
        user = context.user_data.get('editing_user_data')
        
        success = UserService.reset_player_level(telegram_id, admin_id)
        
        if success:
            context.user_data['editing_user_data']['player_level'] = None
            
            keyboard = [
                [InlineKeyboardButton("← К карточке пользователя", callback_data="show_user_card_return")],
                [InlineKeyboardButton("🛠️ Админ панель", callback_data="admin_panel_return")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ Уровень сброшен!\n\n"
                f"Пользователь: {user['full_name']}\n"
                f"Уровень: Не установлен",
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text("❌ Ошибка при сбросе уровня")
        
        return UserEditStates.SHOWING_USER_CARD  # ← ИЗМЕНИЛИ! Было END
        
    except Exception as e:
        logger.error(f"Error in reset_user_level: {e}")
        await query.edit_message_text("Произошла ошибка")
        return END

# ========================================
# ОТМЕНА И ВОЗВРАТ
# ========================================

async def cancel_user_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена редактирования пользователя"""
    try:
        query = update.callback_query
        await query.answer()
        
        from utils.admin_keyboards import get_admin_panel_keyboard, get_admin_panel_text
        
        await query.edit_message_text(
            get_admin_panel_text(), 
            reply_markup=get_admin_panel_keyboard()
        )
        
        context.user_data.clear()
        return END
        
    except Exception as e:
        logger.error(f"Error in cancel_user_edit: {e}")
        return END

async def show_user_card_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат к карточке пользователя через callback"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = context.user_data.get('editing_user_data')
        
        if not user:
            await query.edit_message_text("Ошибка: данные пользователя не найдены")
            return END
        
        # Обновляем данные пользователя
        telegram_id = context.user_data.get('editing_user_id')
        updated_user = UserService.get_user_by_telegram_id(telegram_id)
        
        if updated_user:
            context.user_data['editing_user_data'] = updated_user
            user = updated_user
        
        # Формируем текст карточки
        text = "👤 Карточка пользователя\n\n"
        text += f"📝 ФИО: {user['full_name']}\n"
        text += f"📱 Телефон: {user['phone_number']}\n"
        text += f"🆔 Telegram ID: {user['telegram_id']}\n"
        
        # Форматируем дату регистрации
        if user['created_at']:
            from datetime import datetime
            try:
                created_date = datetime.fromisoformat(user['created_at'])
                text += f"📅 Регистрация: {created_date.strftime('%d.%m.%Y')}\n\n"
            except:
                text += f"📅 Регистрация: {user['created_at'][:10]}\n\n"
        else:
            text += f"📅 Регистрация: не указано\n\n"
        
        # Добавляем информацию об уровне
        if user['player_level']:
            level_display = format_level_display(user['player_level'])
            text += f"{level_display}\n"
            
            # Форматируем дату обновления уровня
            if user['player_level_updated_at']:
                from datetime import datetime
                try:
                    updated_date = datetime.fromisoformat(user['player_level_updated_at'])
                    text += f"🕒 Обновлён: {updated_date.strftime('%d.%m.%Y %H:%M')}\n"
                except:
                    text += f"🕒 Обновлён: {user['player_level_updated_at'][:16]}\n"
        else:
            text += "⭐ Уровень: Не установлен\n"
        
        keyboard = [
            [InlineKeyboardButton("✏️ Изменить ФИО", callback_data="edit_user_name")],
            [InlineKeyboardButton("⭐ Изменить уровень", callback_data="edit_user_level")],
            [InlineKeyboardButton("🔄 Найти другого пользователя", callback_data="edit_user")],
            [InlineKeyboardButton("← Админ панель", callback_data="admin_panel_return")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in show_user_card_callback: {e}")
        await query.edit_message_text("Произошла ошибка")