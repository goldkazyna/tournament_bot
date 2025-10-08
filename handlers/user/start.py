from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import logging
from services.user_service import UserService
from utils.keyboards import get_phone_keyboard, remove_keyboard, get_main_menu_keyboard

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    try:
        user = update.effective_user
        telegram_id = user.id
        
        logger.info(f"User {telegram_id} ({user.username}) started the bot")
        
        # Проверяем, зарегистрирован ли пользователь
        if UserService.is_user_registered(telegram_id):
            # Показываем главное меню для зарегистрированного пользователя
            user_data = UserService.get_user_by_telegram_id(telegram_id)
            
            welcome_message = f"🎾 Добро пожаловать, {user_data['full_name']}!\n\nВыберите действие:"
            
            await update.message.reply_text(
                welcome_message, 
                reply_markup=get_main_menu_keyboard()
            )
        else:
            # Приглашаем к регистрации с инлайн кнопкой
            welcome_message = f"""🎾 Добро пожаловать в турнирного бота по падел теннису!

Привет, {user.first_name}! 

Этот бот поможет тебе:
- Зарегистрироваться в системе
- Участвовать в турнирах по падел теннису  
- Следить за результатами

Для участия в турнирах необходимо зарегистрироваться:"""
            
            keyboard = [
                [InlineKeyboardButton("📝 Зарегистрироваться", callback_data="start_registration")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(welcome_message, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
        
async def enter_cabinet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Войти в личный кабинет' после регистрации"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        telegram_id = user.id
        
        # Проверяем, зарегистрирован ли пользователь
        if UserService.is_user_registered(telegram_id):
            user_data = UserService.get_user_by_telegram_id(telegram_id)
            
            welcome_message = f"🎾 Добро пожаловать, {user_data['full_name']}!\n\nВыберите действие:"
            
            await query.edit_message_text(welcome_message)
            await query.message.reply_text(
                "Главное меню:", 
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await query.edit_message_text(
                "❌ Ошибка: пользователь не найден.\n"
                "Попробуйте команду /start"
            )
        
    except Exception as e:
        logger.error(f"Error in enter_cabinet: {e}")
        await query.edit_message_text("Произошла ошибка")