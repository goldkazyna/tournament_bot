from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import logging
from config import ADMIN_IDS, SUPER_ADMIN_IDS, MODERATOR_IDS
from utils.admin_keyboards import get_admin_panel_keyboard, get_moderator_panel_keyboard, get_admin_panel_text, get_moderator_panel_text

logger = logging.getLogger(__name__)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главная панель администратора"""
    try:
        user_id = update.effective_user.id
        # ВРЕМЕННОЕ ЛОГИРОВАНИЕ ДЛЯ ОТЛАДКИ
        # Проверяем права доступа
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("У вас нет прав администратора.")
            return
        
        # Определяем уровень доступа
        if user_id in SUPER_ADMIN_IDS:
            # Полная админ панель
            reply_markup = get_admin_panel_keyboard()
            text = get_admin_panel_text()
        elif user_id in MODERATOR_IDS:
            # Только модерация
            reply_markup = get_moderator_panel_keyboard()
            text = get_moderator_panel_text()
        else:
            await update.message.reply_text("У вас нет прав администратора.")
            return
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in admin_panel: {e}")
        await update.message.reply_text("Произошла ошибка.")

def is_admin(user_id: int) -> bool:
    """Проверка прав администратора (любой уровень)"""
    return user_id in ADMIN_IDS

def is_super_admin(user_id: int) -> bool:
    """Проверка прав главного администратора"""
    return user_id in SUPER_ADMIN_IDS

def is_moderator(user_id: int) -> bool:
    """Проверка прав модератора"""
    return user_id in MODERATOR_IDS
    
async def export_all_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Экспорт всех пользователей в Excel - ТОЛЬКО ДЛЯ ГЛАВНОГО АДМИНА"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # Проверяем, что это главный админ
        if not is_super_admin(user_id):
            await query.edit_message_text("Нет прав доступа. Эта функция доступна только главному администратору.")
            return
        
        # Получаем всех пользователей
        from database.connection import db
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT telegram_id, full_name, phone_number, skill_level, 
                       age_category, created_at
                FROM users 
                WHERE telegram_id > 0
                ORDER BY created_at DESC
            """)
            
            users = cursor.fetchall()
        
        if not users:
            await query.edit_message_text("Нет пользователей для экспорта")
            return
        
        # Создаем Excel файл
        import io
        from datetime import datetime
        import xlsxwriter
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Пользователи')
        
        # Форматы
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#366092',
            'font_color': 'white',
            'align': 'center'
        })
        
        cell_format = workbook.add_format({'bg_color': '#F8F9FA'})
        
        # Заголовки
        headers = ['Telegram ID', 'ФИО', 'Телефон', 'Уровень игры', 'Возрастная категория', 'Дата регистрации']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Данные пользователей
        for row, user in enumerate(users, 1):
            worksheet.write(row, 0, user[0], cell_format)
            worksheet.write(row, 1, user[1], cell_format)
            worksheet.write(row, 2, user[2], cell_format)
            worksheet.write(row, 3, user[3], cell_format)
            worksheet.write(row, 4, user[4], cell_format)
            worksheet.write(row, 5, user[5][:16], cell_format)
        
        # Автоподбор ширины колонок
        worksheet.set_column('A:A', 12)
        worksheet.set_column('B:B', 25)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 15)
        worksheet.set_column('E:E', 18)
        worksheet.set_column('F:F', 18)
        
        workbook.close()
        output.seek(0)
        
        # Отправляем файл
        filename = f"all_users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=output,
            filename=filename,
            caption=f"📊 Все пользователи бота\nВсего пользователей: {len(users)}"
        )
        
        # Отправляем админ панель отдельным сообщением
        from utils.admin_keyboards import get_admin_panel_keyboard, get_admin_panel_text
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=get_admin_panel_text(),
            reply_markup=get_admin_panel_keyboard()
        )
        
        # Удаляем исходное сообщение
        await query.delete_message()
        
    except Exception as e:
        logger.error(f"Error in export_all_users: {e}")
        try:
            await query.edit_message_text("Произошла ошибка при экспорте")
        except:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Произошла ошибка при экспорте"
            )