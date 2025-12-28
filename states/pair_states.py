from telegram.ext import ConversationHandler

# Состояния для парной регистрации
class PairRegistrationStates:
    WAITING_PARTNER_ID = 100

# Для завершения разговора
END = ConversationHandler.END