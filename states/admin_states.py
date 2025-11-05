from telegram.ext import ConversationHandler

# Состояния для создания турнира
class TournamentCreationStates:
    WAITING_TYPE = 0
    WAITING_NAME = 1
    WAITING_DATE = 2
    WAITING_LOCATION = 3
    WAITING_FORMAT = 4
    WAITING_ENTRY_FEE = 5
    WAITING_DESCRIPTION = 6
    WAITING_LEVEL_RESTRICTION = 7    # ← НОВОЕ: выбор типа ограничения
    WAITING_MIN_LEVEL = 8            # ← НОВОЕ: выбор минимального уровня
    WAITING_MAX_LEVEL = 9            # ← НОВОЕ: выбор максимального уровня

# Состояния для редактирования турнира
class TournamentEditStates:
    SELECTING_TOURNAMENT = 10
    EDITING_NAME = 11
    EDITING_DATE = 12
    EDITING_LOCATION = 13
    EDITING_FORMAT = 14
    EDITING_ENTRY_FEE = 15
    EDITING_DESCRIPTION = 16

# Состояния для редактирования пользователя
class UserEditStates:
    WAITING_TELEGRAM_ID = 30      # Ожидание ввода Telegram ID
    SHOWING_USER_CARD = 31        # Показ карточки пользователя
    EDITING_NAME = 32             # Редактирование ФИО
    SELECTING_CATEGORY = 33       # Выбор категории уровня (C, B, A)
    SELECTING_LEVEL = 34          # Выбор конкретного уровня (3.5, 4.0...)
    
# Для завершения разговора
END = ConversationHandler.END