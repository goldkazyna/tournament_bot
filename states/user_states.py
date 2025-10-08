from telegram.ext import ConversationHandler

# Состояния для регистрации пользователя
class RegistrationStates:
    WAITING_FULL_NAME = 1
    WAITING_PHONE = 2

# Состояния для редактирования профиля
class ProfileStates:
    EDITING_NAME = 3

# Для завершения разговора
END = ConversationHandler.END