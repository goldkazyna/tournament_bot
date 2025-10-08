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

class TournamentEditStates:
    SELECTING_TOURNAMENT = 10
    EDITING_NAME = 11
    EDITING_DATE = 12
    EDITING_LOCATION = 13
    EDITING_FORMAT = 14
    EDITING_ENTRY_FEE = 15
    EDITING_DESCRIPTION = 16
    
# Для завершения разговора
END = ConversationHandler.END