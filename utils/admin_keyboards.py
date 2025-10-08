from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def get_admin_panel_keyboard():
    """Получить клавиатуру админ панели - ПОЛНЫЙ ДОСТУП"""
    keyboard = [
        [InlineKeyboardButton("➕ Создать турнир", callback_data="create_tournament")],
        [InlineKeyboardButton("✏️ Редактировать турнир", callback_data="edit_tournament")],
        [InlineKeyboardButton("⚖️ Модерация заявок", callback_data="admin_moderation")],
        [InlineKeyboardButton("📋 Список турниров", callback_data="admin_tournaments")],
        [InlineKeyboardButton("📊 Выгрузить всех пользователей", callback_data="users_export")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_moderator_panel_keyboard():
    """Получить клавиатуру модератора - ТОЛЬКО МОДЕРАЦИЯ"""
    keyboard = [
        [InlineKeyboardButton("⚖️ Модерация заявок", callback_data="admin_moderation")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_panel_text():
    """Получить текст админ панели"""
    return "🛠️ Панель администратора\n\nВыберите действие:"

def get_moderator_panel_text():
    """Получить текст панели модератора"""
    return "⚖️ Панель модератора\n\nВы можете модерировать заявки на турниры:"