import logging
import asyncio
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from config import BOT_TOKEN, LOG_LEVEL, LOG_FILE
from handlers.user.start import start_command, enter_cabinet
from handlers.user.registration import (
    start_registration, ask_full_name, handle_contact_share, cancel_registration
)
from handlers.user.tournaments import show_tournaments_list, show_tournament_details, back_to_tournaments
from handlers.admin.panel import admin_panel, export_all_users
from handlers.admin.tournament_crud import (
    start_tournament_creation, ask_tournament_name, ask_tournament_date,
    ask_tournament_location, ask_tournament_format, ask_tournament_entry_fee,
    ask_level_restriction, handle_level_restriction_choice,  # ← НОВЫЕ
    handle_min_level_selection, handle_max_level_selection,  # ← НОВЫЕ
    finish_tournament_creation_with_levels,  # ← НОВОЕ
    cancel_tournament_creation, return_to_admin_panel,
    handle_tournament_type, cancel_tournament_creation_callback,
    start_tournament_edit, select_tournament_for_edit, edit_tournament_field,
    handle_field_edit, finish_tournament_edit, cancel_field_edit
)
from handlers.common.menu_handler import handle_menu_buttons
from states.user_states import RegistrationStates, ProfileStates
from states.admin_states import TournamentCreationStates, TournamentEditStates, UserEditStates
from database.connection import db
from handlers.user.participation import join_tournament, leave_tournament, confirm_leave_tournament, cancel_leave_tournament
from handlers.admin.moderation import (
    show_moderation_menu, show_tournament_moderation, 
    show_participant_moderation, approve_participant, reject_participant
)
from handlers.user.participation import handle_confirmed_status, handle_pending_status
from handlers.admin.tournament_list import (
    show_admin_tournaments, show_tournament_management, archive_tournament, 
    export_participants, show_participants_list, manage_participant, remove_participant
)
from handlers.user.profile import (
    start_edit_profile, handle_new_name, save_profile, cancel_edit
)
# НОВЫЕ ИМПОРТЫ для редактирования пользователей
from handlers.admin.user_edit import (
    start_user_edit, find_user_by_id, start_edit_name, handle_new_name as handle_user_new_name,
    start_edit_level, select_level_category, save_selected_level, reset_user_level,
    cancel_user_edit, show_user_card_callback
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, LOG_LEVEL),
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Главная функция запуска бота"""
    try:
        if not BOT_TOKEN:
            logger.error("BOT_TOKEN не найден в .env файле!")
            return
        
        logger.info("Инициализация бота...")
        
        application = Application.builder().token(BOT_TOKEN).build()
        
        # ===============================
        # ConversationHandler-ы (добавляем ПЕРВЫМИ)
        # ===============================
        
        # Обработчик регистрации
        registration_handler = ConversationHandler(
            entry_points=[
                CommandHandler("register", start_registration),
                CallbackQueryHandler(start_registration, pattern="^start_registration$")
            ],
            states={
                RegistrationStates.WAITING_FULL_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, ask_full_name)
                ],
                RegistrationStates.WAITING_PHONE: [
                    MessageHandler(filters.CONTACT, handle_contact_share),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_contact_share)
                ]
            },
            fallbacks=[CommandHandler("cancel", cancel_registration)],
            per_message=False
        )
        
        tournament_creation_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(start_tournament_creation, pattern="^create_tournament$")
            ],
            states={
                TournamentCreationStates.WAITING_TYPE: [
                    CallbackQueryHandler(handle_tournament_type, pattern="^tournament_type_")
                ],
                TournamentCreationStates.WAITING_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, ask_tournament_name)
                ],
                TournamentCreationStates.WAITING_DATE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, ask_tournament_date)
                ],
                TournamentCreationStates.WAITING_LOCATION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, ask_tournament_location)
                ],
                TournamentCreationStates.WAITING_FORMAT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, ask_tournament_format)
                ],
                TournamentCreationStates.WAITING_ENTRY_FEE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, ask_tournament_entry_fee)
                ],
                TournamentCreationStates.WAITING_DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, ask_level_restriction)  # ← ИЗМЕНИЛИ!
                ],
                # НОВЫЕ СОСТОЯНИЯ:
                TournamentCreationStates.WAITING_LEVEL_RESTRICTION: [
                    CallbackQueryHandler(handle_level_restriction_choice, pattern="^level_(open|restricted)$")
                ],
                TournamentCreationStates.WAITING_MIN_LEVEL: [
                    CallbackQueryHandler(handle_min_level_selection, pattern="^minlevel_")
                ],
                TournamentCreationStates.WAITING_MAX_LEVEL: [
                    CallbackQueryHandler(handle_max_level_selection, pattern="^maxlevel_")
                ]
            },
            fallbacks=[
                CommandHandler("cancel", cancel_tournament_creation),
                CallbackQueryHandler(cancel_tournament_creation_callback, pattern="^admin_panel_return$")
            ],
            per_message=False
        )
        
        # ConversationHandler для редактирования профиля
        profile_edit_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(start_edit_profile, pattern="^edit_profile$")
            ],
            states={
                ProfileStates.EDITING_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_name)
                ]
            },
            fallbacks=[],
            per_message=False
        )
        
        # Обработчик редактирования турнира
        tournament_edit_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(start_tournament_edit, pattern="^edit_tournament$")
            ],
            states={
                TournamentEditStates.SELECTING_TOURNAMENT: [
                    CallbackQueryHandler(select_tournament_for_edit, pattern="^edit_tournament_[0-9]+$"),
                    CallbackQueryHandler(edit_tournament_field, pattern="^edit_field_"),
                    CallbackQueryHandler(finish_tournament_edit, pattern="^finish_edit$")
                ],
                TournamentEditStates.EDITING_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_field_edit)
                ],
                TournamentEditStates.EDITING_DATE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_field_edit)
                ],
                TournamentEditStates.EDITING_LOCATION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_field_edit)
                ],
                TournamentEditStates.EDITING_FORMAT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_field_edit)
                ],
                TournamentEditStates.EDITING_ENTRY_FEE: [  
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_field_edit)
                ],
                TournamentEditStates.EDITING_DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_field_edit)
                ]
            },
            fallbacks=[
                CallbackQueryHandler(cancel_field_edit, pattern="^cancel_field_edit$"),
                CallbackQueryHandler(cancel_tournament_creation_callback, pattern="^admin_panel_return$")
            ],
            per_message=False
        )
        
        # ===============================
        # НОВЫЙ ConversationHandler для редактирования пользователей
        # ===============================
        user_edit_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(start_user_edit, pattern="^edit_user$")
            ],
            states={
                UserEditStates.WAITING_TELEGRAM_ID: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, find_user_by_id)
                ],
                UserEditStates.SHOWING_USER_CARD: [
                    CallbackQueryHandler(start_edit_name, pattern="^edit_user_name$"),
                    CallbackQueryHandler(start_edit_level, pattern="^edit_user_level$"),
                    CallbackQueryHandler(show_user_card_callback, pattern="^show_user_card_return$")
                ],
                UserEditStates.EDITING_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_new_name)
                ],
                UserEditStates.SELECTING_CATEGORY: [
                    CallbackQueryHandler(select_level_category, pattern="^select_category_"),
                    CallbackQueryHandler(reset_user_level, pattern="^reset_level$")
                ],
                UserEditStates.SELECTING_LEVEL: [
                    CallbackQueryHandler(save_selected_level, pattern="^set_level_"),
                    CallbackQueryHandler(start_edit_level, pattern="^edit_user_level$")
                ]
            },
            fallbacks=[
                CallbackQueryHandler(cancel_user_edit, pattern="^cancel_user_edit$"),
                CallbackQueryHandler(cancel_user_edit, pattern="^admin_panel_return$")
            ],
            per_message=False
        )
        
        # ===============================
        # Добавляем обработчики в правильном порядке
        # ===============================
        
        # 1. Команды
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("admin", admin_panel))
        application.add_handler(CommandHandler("tournaments", show_tournaments_list))
        
        # 2. ConversationHandler-ы (ВАЖНО: добавляем ПЕРЕД callback обработчиками)
        application.add_handler(registration_handler)
        application.add_handler(tournament_creation_handler)
        application.add_handler(profile_edit_handler)
        application.add_handler(tournament_edit_handler)
        application.add_handler(user_edit_handler)  # ← НОВЫЙ HANDLER!
        
        # 3. Callback обработчики для турниров
        application.add_handler(CallbackQueryHandler(show_tournament_details, pattern="^tournament_"))
        application.add_handler(CallbackQueryHandler(back_to_tournaments, pattern="^back_to_tournaments$"))
        application.add_handler(CallbackQueryHandler(join_tournament, pattern="^join_"))
        application.add_handler(CallbackQueryHandler(leave_tournament, pattern="^leave_"))
        application.add_handler(CallbackQueryHandler(confirm_leave_tournament, pattern="^confirm_leave_"))
        application.add_handler(CallbackQueryHandler(cancel_leave_tournament, pattern="^cancel_leave_"))
        
        # 4. Обработчики участия
        application.add_handler(CallbackQueryHandler(handle_confirmed_status, pattern="^confirmed_"))
        application.add_handler(CallbackQueryHandler(handle_pending_status, pattern="^pending_"))
        
        # 5. Админские обработчики
        application.add_handler(CallbackQueryHandler(show_moderation_menu, pattern="^admin_moderation$"))
        application.add_handler(CallbackQueryHandler(show_tournament_moderation, pattern="^moderate_"))
        application.add_handler(CallbackQueryHandler(show_participant_moderation, pattern="^participant_"))
        application.add_handler(CallbackQueryHandler(approve_participant, pattern="^approve_"))
        application.add_handler(CallbackQueryHandler(reject_participant, pattern="^reject_"))
        application.add_handler(CallbackQueryHandler(show_admin_tournaments, pattern="^admin_tournaments$"))
        application.add_handler(CallbackQueryHandler(show_tournament_management, pattern="^admin_tournament_"))
        application.add_handler(CallbackQueryHandler(archive_tournament, pattern="^archive_"))
        
        # 6. Управление участниками турниров
        application.add_handler(CallbackQueryHandler(export_participants, pattern="^export_[0-9]+$"))
        application.add_handler(CallbackQueryHandler(show_participants_list, pattern="^participants_list_"))
        application.add_handler(CallbackQueryHandler(manage_participant, pattern="^manage_participant_"))
        application.add_handler(CallbackQueryHandler(remove_participant, pattern="^remove_participant_"))
        
        # 7. Экспорт пользователей
        application.add_handler(CallbackQueryHandler(export_all_users, pattern="^export_all_users$"))
        application.add_handler(CallbackQueryHandler(export_all_users, pattern="^users_export$"))
        
        # 8. Профиль
        application.add_handler(CallbackQueryHandler(save_profile, pattern="^save_profile$"))
        application.add_handler(CallbackQueryHandler(cancel_edit, pattern="^cancel_edit$"))
        application.add_handler(CallbackQueryHandler(enter_cabinet, pattern="^enter_cabinet$"))
        
        # 9. Общие admin обработчики (в конце)
        application.add_handler(CallbackQueryHandler(return_to_admin_panel, pattern="^admin_panel_return$"))
        
        # 10. Обработчик текстовых сообщений (ДОЛЖЕН БЫТЬ ПОСЛЕДНИМ)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_buttons))
        
        logger.info("Бот запущен! Нажмите Ctrl+C для остановки.")
        
        application.run_polling(allowed_updates=["message", "callback_query"])
        
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")

if __name__ == '__main__':
    main()