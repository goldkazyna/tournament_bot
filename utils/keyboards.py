from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu_keyboard():
    """Главное меню с reply кнопками"""
    keyboard = [
        [KeyboardButton("🏆 Турниры"), KeyboardButton("👤 Мой профиль")],
        [KeyboardButton("ℹ️ Помощь"), KeyboardButton("🏠 Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_phone_keyboard():
    """ReplyKeyboard для выбора способа ввода телефона"""
    keyboard = [
        [KeyboardButton("📞 Поделиться номером", request_contact=True)],
        [KeyboardButton("✍️ Ввести вручную")],
        [KeyboardButton("❌ Отменить регистрацию")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def remove_keyboard():
    """Убираем клавиатуру"""
    from telegram import ReplyKeyboardRemove
    return ReplyKeyboardRemove()