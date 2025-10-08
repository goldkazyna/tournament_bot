import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Главные администраторы с полными правами
SUPER_ADMIN_IDS = [7442002163, 7055682806]

# Модераторы (только модерация заявок)
MODERATOR_IDS = [7657145796]

# ВСЕ администраторы (объединяем)
ADMIN_IDS = SUPER_ADMIN_IDS + MODERATOR_IDS

# База данных
DATABASE_PATH = os.getenv('DATABASE_PATH', './database/tournament.db')

# Настройки турнира
MAX_MAIN_PARTICIPANTS = 16
MAX_RESERVE_PARTICIPANTS = 2
PAYMENT_TIMEOUT_MINUTES = 30

# Логирование
LOG_LEVEL = 'WARNING'
LOG_FILE = './logs/bot.log'

# Настройки парных турниров
MAX_PAIR_SLOTS = 8
MAX_PAIR_RESERVE = 2

SEND_NOTIFICATIONS = True