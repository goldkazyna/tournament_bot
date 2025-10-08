from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import logging
from services.tournament_service import TournamentService
from handlers.admin.panel import is_admin, is_super_admin, is_moderator
from services.participation_service import ParticipationService
from config import MAX_MAIN_PARTICIPANTS, MAX_RESERVE_PARTICIPANTS

logger = logging.getLogger(__name__)

async def show_admin_tournaments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список активных турниров для админа"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if not is_super_admin(user_id):
            await query.edit_message_text("Нет прав доступа. Эта функция доступна только главному администратору.")
            return
        if not is_admin(user_id):
            await query.edit_message_text("Нет прав доступа")
            return
        
        tournaments = TournamentService.get_all_tournaments()
        
        if not tournaments:
            from utils.admin_keyboards import get_admin_panel_keyboard, get_admin_panel_text
            keyboard = [[InlineKeyboardButton("← Назад", callback_data="admin_panel_return")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "Нет активных турниров",
                reply_markup=reply_markup
            )
            return
        
        text = "Управление турнирами:\n\n"
        keyboard = []
        
        for tournament in tournaments:
            text += f"🏆 {tournament['name']}\n"
            text += f"📅 {tournament['date']}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"📋 {tournament['name']}", 
                    callback_data=f"admin_tournament_{tournament['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("← Назад", callback_data="admin_panel_return")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in show_admin_tournaments: {e}")
        await query.edit_message_text("Произошла ошибка")

async def show_tournament_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать управление конкретным турниром"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if not is_super_admin(user_id):
            await query.edit_message_text("Нет прав доступа. Эта функция доступна только главному администратору.")
            return
        if not is_admin(user_id):
            await query.edit_message_text("Нет прав доступа")
            return
        
        tournament_id = int(query.data.split("_")[2])
        tournament = TournamentService.get_tournament_by_id(tournament_id)
        
        if not tournament:
            await query.edit_message_text("Турнир не найден")
            return
        
        text = f"Управление турниром:\n\n"
        text += f"🏆 {tournament['name']}\n"
        text += f"📅 {tournament['date']}\n"
        text += f"📍 {tournament['location']}\n"
        text += f"💳 {tournament['entry_fee']}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("📦 Переместить в архив", callback_data=f"archive_{tournament_id}")],
            [InlineKeyboardButton("📊 Выгрузить участников", callback_data=f"export_{tournament_id}")],
            [InlineKeyboardButton("👥 Список участников", callback_data=f"participants_list_{tournament_id}")],
            [InlineKeyboardButton("← К списку турниров", callback_data="admin_tournaments")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in show_tournament_management: {e}")
        await query.edit_message_text("Произошла ошибка")

async def archive_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переместить турнир в архив"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if not is_super_admin(user_id):
            await query.edit_message_text("Нет прав доступа. Эта функция доступна только главному администратору.")
            return
        if not is_admin(user_id):
            await query.edit_message_text("Нет прав доступа")
            return
        
        tournament_id = int(query.data.split("_")[1])
        
        success = TournamentService.archive_tournament(tournament_id)
        
        if success:
            # Создаем кнопку для возврата в админ панель
            keyboard = [
                [InlineKeyboardButton("🛠️ Админ панель", callback_data="admin_panel_return")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "✅ Турнир перемещен в архив!\n\n"
                "Теперь он не отображается в списке активных турниров.",
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text("Ошибка при архивации турнира")
        
    except Exception as e:
        logger.error(f"Error in archive_tournament: {e}")
        await query.edit_message_text("Произошла ошибка")

async def export_participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Экспорт участников турнира в Excel"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if not is_super_admin(user_id):
            await query.edit_message_text("Нет прав доступа. Эта функция доступна только главному администратору.")
            return
        if not is_admin(user_id):
            await query.edit_message_text("Нет прав доступа")
            return
        
        tournament_id = int(query.data.split("_")[1])
        tournament = TournamentService.get_tournament_by_id(tournament_id)
        participants = ParticipationService.get_tournament_participants(tournament_id)
        
        if not tournament:
            await query.edit_message_text("Турнир не найден")
            return
        
        if not participants:
            await query.edit_message_text("Нет участников для экспорта")
            return
        
        # Создаем Excel файл
        import io
        from datetime import datetime
        import xlsxwriter
        
        # Создаем буфер в памяти
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Участники')
        
        # Форматы
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#366092',
            'font_color': 'white',
            'align': 'center'
        })
        
        main_format = workbook.add_format({'bg_color': '#E8F4FD'})
        reserve_format = workbook.add_format({'bg_color': '#FFF2CC'})
        pending_format = workbook.add_format({'bg_color': '#FFE6E6'})
        
        # Заголовки
        headers = ['№', 'ФИО', 'Телефон', 'Статус', 'Тип участия', 'Время регистрации']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Данные участников
        for row, participant in enumerate(participants, 1):
            # Выбираем формат в зависимости от типа и статуса
            if participant['status'] == 'pending':
                cell_format = pending_format
            elif participant['type'] == 'основной':
                cell_format = main_format
            else:
                cell_format = reserve_format
            
            worksheet.write(row, 0, participant['position'], cell_format)
            worksheet.write(row, 1, participant['name'], cell_format)
            worksheet.write(row, 2, participant['phone'], cell_format)
            worksheet.write(row, 3, participant['status_text'], cell_format)
            worksheet.write(row, 4, participant['type'], cell_format)
            worksheet.write(row, 5, participant['registration_time'][:16], cell_format)
        
        # Автоподбор ширины колонок
        worksheet.set_column('A:A', 5)
        worksheet.set_column('B:B', 25)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 12)
        worksheet.set_column('E:E', 12)
        worksheet.set_column('F:F', 18)
        
        workbook.close()
        output.seek(0)
        
        # Отправляем файл
        filename = f"participants_{tournament['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=output,
            filename=filename,
            caption=f"📊 Участники турнира: {tournament['name']}\n"
                   f"Всего участников: {len(participants)}"
        )
        
        # Отправляем админ панель отдельным сообщением
        from utils.admin_keyboards import get_admin_panel_keyboard, get_admin_panel_text
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=get_admin_panel_text(),
            reply_markup=get_admin_panel_keyboard()
        )
        
        # Удаляем исходное сообщение с управлением турниром
        await query.delete_message()
        
    except Exception as e:
        logger.error(f"Error in export_participants: {e}")
        try:
            await query.edit_message_text("Произошла ошибка при экспорте")
        except:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Произошла ошибка при экспорте"
            )

async def show_participants_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список участников с кнопками"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if not is_super_admin(user_id):
            await query.edit_message_text("Нет прав доступа. Эта функция доступна только главному администратору.")
            return
        if not is_admin(user_id):
            await query.edit_message_text("Нет прав доступа")
            return
        
        tournament_id = int(query.data.split("_")[2])
        tournament = TournamentService.get_tournament_by_id(tournament_id)
        participants = ParticipationService.get_tournament_participants(tournament_id)
        
        if not tournament:
            await query.edit_message_text("Турнир не найден")
            return
        
        if not participants:
            keyboard = [
                [InlineKeyboardButton("← Назад к управлению", callback_data=f"admin_tournament_{tournament_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"Турнир: {tournament['name']}\n\n"
                "Участников пока нет",
                reply_markup=reply_markup
            )
            return
        
        text = f"Турнир: {tournament['name']}\n"
        text += f"Участников: {len(participants)}\n\n"
        text += "Выберите участника для управления:\n\n"
        
        keyboard = []
        
        # Основные участники
        main_participants = [p for p in participants if p['position'] <= MAX_MAIN_PARTICIPANTS]
        if main_participants:
            text += "👥 ОСНОВНЫЕ УЧАСТНИКИ:\n"
            for participant in main_participants:
                text += f"{participant['status_icon']} {participant['position']}. {participant['name']}\n"
                keyboard.append([
                    InlineKeyboardButton(
                        f"{participant['status_icon']} {participant['name']}", 
                        callback_data=f"manage_participant_{tournament_id}_{participant['position']}"
                    )
                ])
            text += "\n"
        
        # Резервные участники
        reserve_participants = [p for p in participants if p['position'] > MAX_MAIN_PARTICIPANTS]
        if reserve_participants:
            text += "📋 РЕЗЕРВИСТЫ:\n"
            for participant in reserve_participants:
                text += f"{participant['status_icon']} {participant['position']}. {participant['name']}\n"
                keyboard.append([
                    InlineKeyboardButton(
                        f"{participant['status_icon']} {participant['name']}", 
                        callback_data=f"manage_participant_{tournament_id}_{participant['position']}"
                    )
                ])
        
        keyboard.append([InlineKeyboardButton("← Назад к управлению", callback_data=f"admin_tournament_{tournament_id}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in show_participants_list: {e}")
        await query.edit_message_text("Произошла ошибка")

async def manage_participant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Управление конкретным участником"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if not is_super_admin(user_id):
            await query.edit_message_text("Нет прав доступа. Эта функция доступна только главному администратору.")
            return
        if not is_admin(user_id):
            await query.edit_message_text("Нет прав доступа")
            return
        
        # Парсим данные: manage_participant_tournament_id_position
        data_parts = query.data.split("_")
        tournament_id = int(data_parts[2])
        position = int(data_parts[3])
        
        tournament = TournamentService.get_tournament_by_id(tournament_id)
        participants = ParticipationService.get_tournament_participants(tournament_id)
        
        # Находим участника по позиции
        participant = None
        for p in participants:
            if p['position'] == position:
                participant = p
                break
        
        if not participant:
            await query.edit_message_text("Участник не найден")
            return
        
        text = f"Управление участником:\n\n"
        text += f"🏆 Турнир: {tournament['name']}\n"
        text += f"👤 Участник: {participant['name']}\n"
        text += f"📱 Телефон: {participant['phone']}\n"
        text += f"📍 Позиция: #{participant['position']} ({participant['type']})\n"
        text += f"⭐ Статус: {participant['status_text']}\n"
        text += f"📅 Регистрация: {participant['registration_time'][:16]}\n"
        
        keyboard = [
            [InlineKeyboardButton("🗑️ Удалить из турнира", callback_data=f"remove_participant_{tournament_id}_{position}")],
            [InlineKeyboardButton("← Назад к списку", callback_data=f"participants_list_{tournament_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in manage_participant: {e}")
        await query.edit_message_text("Произошла ошибка")

async def remove_participant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удалить участника из турнира"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if not is_super_admin(user_id):
            await query.edit_message_text("Нет прав доступа. Эта функция доступна только главному администратору.")
            return
        if not is_admin(user_id):
            await query.edit_message_text("Нет прав доступа")
            return
        
        # Парсим данные
        data_parts = query.data.split("_")
        tournament_id = int(data_parts[2])
        position = int(data_parts[3])
        
        tournament = TournamentService.get_tournament_by_id(tournament_id)
        participants = ParticipationService.get_tournament_participants(tournament_id)
        
        # Находим участника
        participant = None
        participant_user_id = None
        for p in participants:
            if p['position'] == position:
                participant = p
                # Получаем telegram_id участника
                from database.connection import db
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT telegram_id FROM users WHERE full_name = ? AND phone_number = ?", 
                                 (p['name'], p['phone']))
                    result = cursor.fetchone()
                    if result:
                        participant_user_id = result[0]
                break
        
        if not participant or not participant_user_id:
            await query.edit_message_text("Участник не найден")
            return
        
        # Удаляем участника
        success = ParticipationService.remove_participant(participant_user_id, tournament_id)
        
        if success:
            # Уведомляем участника
            if participant_user_id > 0:  # Добавить эту проверку
                try:
                    await context.bot.send_message(
                        chat_id=participant_user_id,
                        text=f"❌ Вы были исключены из турнира\n\n"
                             f"Турнир: {tournament['name']}\n"
                             f"Причина: Решение администратора\n\n"
                             f"При необходимости вы можете записаться заново."
                    )
                except Exception as e:
                    logger.error(f"Failed to notify removed participant {participant_user_id}: {e}")
            
            keyboard = [
                [InlineKeyboardButton("← К списку участников", callback_data=f"participants_list_{tournament_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ Участник удален из турнира!\n\n"
                f"Участник: {participant['name']}\n"
                f"Турнир: {tournament['name']}\n\n"
                f"Уведомление отправлено участнику.",
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text("Ошибка при удалении участника")
        
    except Exception as e:
        logger.error(f"Error in remove_participant: {e}")
        await query.edit_message_text("Произошла ошибка")