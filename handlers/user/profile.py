from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import logging
from services.user_service import UserService
from states.user_states import ProfileStates
from utils.keyboards import get_main_menu_keyboard
from levels import format_level_display

logger = logging.getLogger(__name__)

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать профиль пользователя"""
    try:
        user_id = update.effective_user.id
        user_data = UserService.get_user_by_telegram_id(user_id)
        
        if not user_data:
            await update.message.reply_text(
                "Профиль не найден. Пройдите регистрацию командой /start",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        text = f"👤 Ваш профиль:\n\n"
        text += f"📝 ФИО: {user_data['full_name']}\n"
        text += f"📱 Телефон: {user_data['phone_number']}\n\n"
        
        # Добавляем информацию об уровне
        if user_data['player_level']:
            level_display = format_level_display(user_data['player_level'])
            text += f"{level_display}\n"
        else:
            text += "⭐ Уровень: Не установлен\n"
            text += "💡 Уровень устанавливается администратором\n"
        
        keyboard = [
            [InlineKeyboardButton("✏️ Редактировать ФИО", callback_data="edit_profile")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            text, 
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in show_profile: {e}")
        await update.message.reply_text(
            "Произошла ошибка при получении профиля",
            reply_markup=get_main_menu_keyboard()
        )

async def start_edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать редактирование профиля"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        user_data = UserService.get_user_by_telegram_id(user_id)
        
        if not user_data:
            await query.edit_message_text("Профиль не найден")
            return ConversationHandler.END
        
        context.user_data['editing_profile'] = True
        context.user_data['original_name'] = user_data['full_name']
        
        await query.edit_message_text(
            f"Редактирование ФИО\n\n"
            f"Текущее значение: {user_data['full_name']}\n\n"
            f"Введите новое ФИО:"
        )
        
        return ProfileStates.EDITING_NAME
        
    except Exception as e:
        logger.error(f"Error in start_edit_profile: {e}")
        await query.edit_message_text("Произошла ошибка")
        return ConversationHandler.END

async def handle_new_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработать новое ФИО"""
    try:
        new_name = update.message.text.strip()
        
        if len(new_name) < 2:
            await update.message.reply_text(
                "❌ Слишком короткое имя. Введите корректное ФИО:",
                reply_markup=get_main_menu_keyboard()
            )
            return ProfileStates.EDITING_NAME
        
        context.user_data['new_name'] = new_name
        original_name = context.user_data.get('original_name', 'Не указано')
        
        keyboard = [
            [InlineKeyboardButton("✅ Сохранить", callback_data="save_profile")],
            [InlineKeyboardButton("❌ Отменить", callback_data="cancel_edit")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Подтвердите изменения:\n\n"
            f"Было: {original_name}\n"
            f"Будет: {new_name}\n\n"
            f"Сохранить изменения?",
            reply_markup=reply_markup
        )
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in handle_new_name: {e}")
        await update.message.reply_text(
            "Произошла ошибка",
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END

async def save_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранить изменения профиля"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        new_name = context.user_data.get('new_name')
        
        if not new_name:
            await query.edit_message_text("Ошибка: новое имя не найдено")
            return
        
        success = UserService.update_user_name(user_id, new_name)
        
        if success:
            await query.edit_message_text(
                f"✅ Данные успешно изменены!\n\n"
                f"Новое ФИО: {new_name}"
            )
            
            # Отправляем главное меню
            await query.message.reply_text(
                "Выберите действие:",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await query.edit_message_text("Ошибка при сохранении данных")
        
        context.user_data.clear()
        
    except Exception as e:
        logger.error(f"Error in save_profile: {e}")
        await query.edit_message_text("Произошла ошибка")

async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отменить редактирование"""
    try:
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text("❌ Редактирование отменено")
        
        # Отправляем главное меню
        await query.message.reply_text(
            "Выберите действие:",
            reply_markup=get_main_menu_keyboard()
        )
        
        context.user_data.clear()
        
    except Exception as e:
        logger.error(f"Error in cancel_edit: {e}")
        await query.edit_message_text("Произошла ошибка")