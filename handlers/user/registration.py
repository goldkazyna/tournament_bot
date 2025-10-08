from telegram import Update, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import logging
from states.user_states import RegistrationStates, END
from services.user_service import UserService
from utils.keyboards import get_phone_keyboard, remove_keyboard, get_main_menu_keyboard
logger = logging.getLogger(__name__)

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинаем процесс регистрации"""
    try:
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            telegram_id = query.from_user.id
        else:
            telegram_id = update.effective_user.id
        
        if UserService.is_user_registered(telegram_id):
            await update.effective_message.reply_text(
                "✅ Вы уже зарегистрированы в системе!\n"
                "Используйте /start для доступа к главному меню."
            )
            return END
        
        text = "📝 Начинаем регистрацию!\n\nВведите ваше полное имя (ФИО):"
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        
        return RegistrationStates.WAITING_FULL_NAME
        
    except Exception as e:
        logger.error(f"Error in start_registration: {e}")
        await update.effective_message.reply_text("Произошла ошибка. Попробуйте позже.")
        return END

async def ask_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатываем ввод ФИО"""
    try:
        full_name = update.message.text.strip()
        
        if len(full_name) < 2:
            await update.message.reply_text(
                "❌ Слишком короткое имя. Пожалуйста, введите ваше полное имя:"
            )
            return RegistrationStates.WAITING_FULL_NAME
        
        context.user_data['full_name'] = full_name
        
        await update.message.reply_text(
            f"✅ Отлично, {full_name}!\n\n"
            f"📱 Теперь нам нужен ваш номер телефона:\n\n"
            f"💡 <b>Для кнопки 'Поделиться номером' используйте меню возле кнопки прикрепить файл</b> (📎)",
            reply_markup=get_phone_keyboard(),
            parse_mode='HTML'
        )
        
        return RegistrationStates.WAITING_PHONE
        
    except Exception as e:
        logger.error(f"Error in ask_full_name: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
        return END
        
async def handle_contact_share(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатываем все действия с телефоном"""
    try:
        # Если пришел контакт
        if update.message.contact:
            phone_number = update.message.contact.phone_number
            
        # Если пришел текст
        elif update.message.text:
            text = update.message.text
            
            if text == "❌ Отменить регистрацию":
                await update.message.reply_text(
                    "❌ Регистрация отменена.",
                    reply_markup=remove_keyboard()
                )
                context.user_data.clear()
                return END
                
            elif text == "✍️ Ввести вручную":
                await update.message.reply_text(
                    "📱 Введите ваш номер телефона:",
                    reply_markup=remove_keyboard()
                )
                return RegistrationStates.WAITING_PHONE
                
            elif text == "📞 Поделиться номером":
                await update.message.reply_text(
                    "❌ Нажмите на кнопку для передачи контакта.",
                    reply_markup=get_phone_keyboard()
                )
                return RegistrationStates.WAITING_PHONE
                
            else:
                # Ручной ввод номера
                phone_number = text.strip()
                
                if len(phone_number) < 5:
                    await update.message.reply_text(
                        "❌ Номер слишком короткий. Введите корректный номер:"
                    )
                    return RegistrationStates.WAITING_PHONE
        else:
            return RegistrationStates.WAITING_PHONE

        # Регистрируем пользователя
        telegram_id = update.effective_user.id
        full_name = context.user_data['full_name']
        
        success = UserService.register_user(
            telegram_id=telegram_id,
            full_name=full_name,
            phone_number=phone_number,
            skill_level="Не указано",
            age_category="Не указано"
        )
        
        if success:
            # Создаем инлайн-кнопку для входа в личный кабинет  
            keyboard = [
                [InlineKeyboardButton("🏠 Войти в личный кабинет", callback_data="enter_cabinet")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"🎉 Регистрация завершена!\n\n"
                f"📋 Ваши данные:\n"
                f"• Имя: {full_name}\n"
                f"• Телефон: {phone_number}\n\n"
                f"Теперь вы можете участвовать в турнирах!",
                reply_markup=reply_markup
            )
            context.user_data.clear()
        else:
            await update.message.reply_text(
                "❌ Ошибка сохранения. Попробуйте /register еще раз",
                reply_markup=remove_keyboard()
            )
        
        return END
        
    except Exception as e:
        logger.error(f"Error in handle_contact_share: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
        return END

async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена регистрации"""
    await update.message.reply_text(
        "❌ Регистрация отменена.",
        reply_markup=remove_keyboard()
    )
    context.user_data.clear()
    return END

async def cancel_registration_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена через callback"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("❌ Регистрация отменена.")
    context.user_data.clear()
    return END