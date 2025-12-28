from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import logging
from services.user_service import UserService
from services.tournament_service import TournamentService
from services.pair_service import PairService
from states.pair_states import PairRegistrationStates, END
from levels import check_level_in_range, get_level_name
from config import MAX_PAIR_SLOTS, MAX_PAIR_RESERVE, PAYMENT_TIMEOUT_MINUTES

logger = logging.getLogger(__name__)

async def join_pair_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало регистрации на парный турнир"""
    try:
        query = update.callback_query
        await query.answer()
        

        # ============================================
        
        user_id = query.from_user.id
        parts = query.data.split("_")
        if len(parts) == 3 and parts[1] == "pair":
            tournament_id = int(parts[2])  # join_pair_138
        else:
            tournament_id = int(parts[1])  # join_138 (из deep link)
        

        
        # Проверяем, зарегистрирован ли пользователь в системе
        if not UserService.is_user_registered(user_id):
            await query.edit_message_text(
                "Для участия в турнирах необходимо зарегистрироваться.\n"
                "Используйте команду /start"
            )
            return END
        
        # Проверяем, не записан ли уже
        if PairService.is_user_in_pair(user_id, tournament_id):
            keyboard = [
                [InlineKeyboardButton("Отменить участие", callback_data=f"leave_pair_{tournament_id}")],
                [InlineKeyboardButton("← Назад к турниру", callback_data=f"tournament_{tournament_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "Вы уже записаны на этот турнир в паре!\n\n"
                "Хотите отменить участие?",
                reply_markup=reply_markup
            )
            return END
        
        # Получаем турнир и проверяем уровень игрока 1
        tournament = TournamentService.get_tournament_by_id(tournament_id)
        user_data = UserService.get_user_by_telegram_id(user_id)
        
        if not tournament:
            await query.edit_message_text("Турнир не найден")
            return END
        
        # Проверяем ограничения по уровню для игрока 1
        if tournament.get('level_restriction') == 'restricted':
            player_level = user_data.get('player_level')
            min_level = tournament.get('min_level')
            max_level = tournament.get('max_level')
            
            # Проверка 1: Уровень не установлен
            if not player_level:
                keyboard = [
                    [InlineKeyboardButton("← Назад к турниру", callback_data=f"tournament_{tournament_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    "❌ Ваш уровень игры не установлен\n\n"
                    "Этот турнир имеет ограничения по уровню.\n"
                    f"Требуемый уровень: {min_level} - {max_level}\n\n"
                    "📱 Для установки вашего уровня свяжитесь с Кристианом:\n"
                    "WhatsApp: +7 771 175 4421",
                    reply_markup=reply_markup
                )
                return END
            
            # Проверка 2: Уровень не подходит по диапазону
            if not check_level_in_range(player_level, min_level, max_level):
                player_level_name = get_level_name(player_level)
                min_level_name = get_level_name(min_level)
                max_level_name = get_level_name(max_level)
                
                keyboard = [
                    [InlineKeyboardButton("← Назад к турниру", callback_data=f"tournament_{tournament_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"❌ К сожалению, вы не можете участвовать в этом турнире\n\n"
                    f"Турнир: {tournament['name']}\n\n"
                    f"Требуемый уровень: {min_level} - {max_level}\n"
                    f"({min_level_name} - {max_level_name})\n\n"
                    f"Ваш уровень: {player_level} ({player_level_name})\n\n"
                    f"Ищите турниры, подходящие вашему уровню! 🎾",
                    reply_markup=reply_markup
                )
                return END
        
        # Уровень игрока 1 подходит - просим ID напарника
        keyboard = [
            [InlineKeyboardButton("❌ Отмена", callback_data=f"tournament_{tournament_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🎾 Регистрация на парный турнир\n\n"
            f"Турнир: {tournament['name']}\n\n"
            f"✅ Ваш уровень подходит\n\n"
            f"Введите Telegram ID вашего напарника:\n\n"
            f"💡 Напарник может узнать свой ID в разделе 'Мой профиль'",
            reply_markup=reply_markup
        )
        
        # Сохраняем tournament_id для следующего шага
        context.user_data['pair_tournament_id'] = tournament_id
        context.user_data['pair_player1_id'] = user_id
        context.user_data['waiting_for_partner_id'] = True
        
        return PairRegistrationStates.WAITING_PARTNER_ID
        
    except Exception as e:
        logger.error(f"Error in join_pair_tournament: {e}")
        await query.edit_message_text("Произошла ошибка при записи на турнир")
        return END


async def handle_partner_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка введённого ID напарника"""
    try:
        logger.warning(f"🔵 handle_partner_id CALLED")
        logger.warning(f"🔵 Message text: {update.message.text}")
        logger.warning(f"🔵 User data: {context.user_data}")
        partner_id_str = update.message.text.strip()
        
        # Проверяем что введено число
        if not partner_id_str.isdigit():
            await update.message.reply_text(
                "❌ Ошибка: введите корректный Telegram ID (только цифры)\n\n"
                "Попробуйте ещё раз:"
            )
            return PairRegistrationStates.WAITING_PARTNER_ID
        
        partner_id = int(partner_id_str)
        player1_id = context.user_data.get('pair_player1_id')
        tournament_id = context.user_data.get('pair_tournament_id')
        
        # Проверка: не указал ли сам себя
        if partner_id == player1_id:
            await update.message.reply_text(
                "❌ Ошибка: вы не можете указать самого себя как напарника!\n\n"
                "Введите Telegram ID другого игрока:"
            )
            return PairRegistrationStates.WAITING_PARTNER_ID
        
        # Ищем напарника в базе
        partner_data = UserService.get_user_by_telegram_id(partner_id)
        
        if not partner_data:
            await update.message.reply_text(
                f"❌ Пользователь с ID {partner_id} не найден в системе\n\n"
                "Возможно, ваш напарник ещё не зарегистрирован в боте.\n"
                "Попросите его использовать команду /start"
            )
            context.user_data.clear()
            return END
        
        # Проверяем что напарник не в другой паре
        if PairService.is_user_in_pair(partner_id, tournament_id):
            await update.message.reply_text(
                f"❌ Извините, {partner_data['full_name']} уже записан в другой паре на этот турнир\n\n"
                "Выберите другого напарника или свяжитесь с организатором."
            )
            context.user_data.clear()
            return END
        
        # Получаем турнир и проверяем уровень напарника
        tournament = TournamentService.get_tournament_by_id(tournament_id)
        
        if tournament.get('level_restriction') == 'restricted':
            partner_level = partner_data.get('player_level')
            min_level = tournament.get('min_level')
            max_level = tournament.get('max_level')
            
            # Проверка: уровень напарника не установлен
            if not partner_level:
                await update.message.reply_text(
                    f"❌ У вашего напарника ({partner_data['full_name']}) не установлен уровень игры\n\n"
                    f"Этот турнир имеет ограничения по уровню.\n"
                    f"Требуемый уровень: {min_level} - {max_level}\n\n"
                    "Попросите напарника связаться с Кристианом для установки уровня:\n"
                    "WhatsApp: +7 771 175 4421"
                )
                context.user_data.clear()
                return END
            
            # Проверка: уровень напарника не подходит
            if not check_level_in_range(partner_level, min_level, max_level):
                partner_level_name = get_level_name(partner_level)
                min_level_name = get_level_name(min_level)
                max_level_name = get_level_name(max_level)
                
                await update.message.reply_text(
                    f"❌ Уровень вашего напарника не подходит для этого турнира\n\n"
                    f"Напарник: {partner_data['full_name']}\n"
                    f"Уровень напарника: {partner_level} ({partner_level_name})\n\n"
                    f"Требуемый уровень: {min_level} - {max_level}\n"
                    f"({min_level_name} - {max_level_name})\n\n"
                    "Выберите другого напарника с подходящим уровнем."
                )
                context.user_data.clear()
                return END
        
        # ВСЁ ОК - создаём пару
        success = PairService.create_pair(tournament_id, player1_id, partner_id)
        
        if success:
            player1_data = UserService.get_user_by_telegram_id(player1_id)
            
            await update.message.reply_text(
                f"✅ Заявка на пару отправлена!\n\n"
                f"🎾 Турнир: {tournament['name']}\n"
                f"👥 Пара:\n"
                f"   • {player1_data['full_name']}\n"
                f"   • {partner_data['full_name']}\n\n"
                f"📊 Статус: Ожидает одобрения\n\n"
                f"⏰ У вас есть {PAYMENT_TIMEOUT_MINUTES} минут для оплаты.\n"
                f"После оплаты дождитесь подтверждения от организатора.\n\n"
                f"💳 Ссылка для оплаты:\n"
                f"https://pay.kaspi.kz/pay/g6b21oa4"
            )
            
            # Уведомляем напарника
            try:
                await context.bot.send_message(
                    chat_id=partner_id,
                    text=f"🎾 Вас записали в пару на турнир!\n\n"
                         f"Турнир: {tournament['name']}\n"
                         f"Партнёр: {player1_data['full_name']}\n\n"
                         f"Ожидайте подтверждения от организатора."
                )
            except Exception as e:
                logger.error(f"Failed to notify partner {partner_id}: {e}")
            
        else:
            await update.message.reply_text(
                "❌ К сожалению, все места на турнире заняты!"
            )
        
        context.user_data.clear()
        return END
        
    except Exception as e:
        logger.error(f"Error in handle_partner_id: {e}")
        await update.message.reply_text("Произошла ошибка при обработке запроса")
        context.user_data.clear()
        return END


async def leave_pair_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрос подтверждения отмены участия в парном турнире"""
    try:
        query = update.callback_query
        await query.answer()
        
        tournament_id = int(query.data.split("_")[2])
        user_id = query.from_user.id
        
        # Получаем информацию о паре
        pair = PairService.get_user_pair(user_id, tournament_id)
        tournament = TournamentService.get_tournament_by_id(tournament_id)
        
        if not pair or not tournament:
            await query.edit_message_text("Информация не найдена")
            return
        
        # Определяем кто напарник
        partner_id = pair['player2_id'] if pair['player1_id'] == user_id else pair['player1_id']
        partner_name = pair['player2_name'] if pair['player1_id'] == user_id else pair['player1_name']
        
        # Спрашиваем подтверждение
        keyboard = [
            [InlineKeyboardButton("✅ Да, отменить участие", callback_data=f"confirm_leave_pair_{tournament_id}")],
            [InlineKeyboardButton("❌ Нет, оставить участие", callback_data=f"cancel_leave_pair_{tournament_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚠️ Подтверждение отмены\n\n"
            f"Турнир: {tournament['name']}\n"
            f"Ваш напарник: {partner_name}\n\n"
            f"⚠️ При отмене будет удалена ВСЯ ПАРА (вы и напарник)!\n\n"
            f"Вы уверены?",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in leave_pair_tournament: {e}")
        await query.edit_message_text("Произошла ошибка")


async def confirm_leave_pair_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждённая отмена участия в парном турнире"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        tournament_id = int(query.data.split("_")[3])
        
        # Получаем информацию о паре ДО удаления
        pair = PairService.get_user_pair(user_id, tournament_id)
        tournament = TournamentService.get_tournament_by_id(tournament_id)
        
        if not pair:
            await query.edit_message_text("Пара не найдена")
            return
        
        # Проверяем был ли турнир полным
        counts_before = PairService.get_pairs_count(tournament_id)
        was_full = counts_before['available_main'] == 0
        
        # Определяем напарника
        partner_id = pair['player2_id'] if pair['player1_id'] == user_id else pair['player1_id']
        partner_name = pair['player2_name'] if pair['player1_id'] == user_id else pair['player1_name']
        
        # Удаляем пару
        success = PairService.remove_pair(tournament_id, user_id)
        
        if success:
            # Уведомляем напарника
            try:
                await context.bot.send_message(
                    chat_id=partner_id,
                    text=f"❌ Ваш партнёр отменил участие в турнире\n\n"
                         f"Турнир: {tournament['name']}\n"
                         f"Партнёр: {query.from_user.first_name}\n\n"
                         f"Ваша пара была удалена из турнира."
                )
            except Exception as e:
                logger.error(f"Failed to notify partner {partner_id}: {e}")
            
            # Если турнир был полным - уведомляем канал
            if was_full:
                import asyncio
                from services.notification_service import NotificationService
                
                asyncio.create_task(
                    NotificationService.notify_slot_available(
                        context.application, tournament
                    )
                )
                logger.info(f"Pair cancelled in full tournament {tournament_id}, notifying channel")
            
            keyboard = [
                [InlineKeyboardButton("← Назад к турниру", callback_data=f"tournament_{tournament_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ Ваше участие в турнире отменено\n\n"
                f"Пара удалена:\n"
                f"• {query.from_user.first_name}\n"
                f"• {partner_name}",
                reply_markup=reply_markup
            )
        else:
            keyboard = [
                [InlineKeyboardButton("← Назад к турниру", callback_data=f"tournament_{tournament_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "❌ Ошибка при отмене участия.",
                reply_markup=reply_markup
            )
        
    except Exception as e:
        logger.error(f"Error in confirm_leave_pair_tournament: {e}")
        await query.edit_message_text("Произошла ошибка")


async def cancel_leave_pair_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена удаления пары - возврат к турниру"""
    try:
        query = update.callback_query
        await query.answer("Участие сохранено")
        
        tournament_id = int(query.data.split("_")[3])
        
        # Редирект обратно к турниру
        keyboard = [
            [InlineKeyboardButton("← Назад к турниру", callback_data=f"tournament_{tournament_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "✅ Участие в турнире сохранено",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in cancel_leave_pair_tournament: {e}")
        await query.edit_message_text("Произошла ошибка")
        
async def cancel_pair_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена регистрации на парный турнир"""
    try:
        query = update.callback_query
        await query.answer("Регистрация отменена")
        
        # Извлекаем tournament_id из callback_data
        # tournament_132 -> ["tournament", "132"]
        tournament_id = int(query.data.split("_")[1])
        
        # Очищаем данные
        context.user_data.clear()
        
        # Возвращаем к турниру
        from handlers.user.tournaments import show_tournament_details
        await show_tournament_details(update, context)
        
        return END
        
    except Exception as e:
        logger.error(f"Error in cancel_pair_registration: {e}")
        await query.edit_message_text("Произошла ошибка")
        return END