from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
    InputFile,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    ChatMemberHandler,
    JobQueue
)
from telegram.constants import ChatMemberStatus

import telegram.error
from config import BOT_TOKEN, WEBAPP_URL
from database import Session, User
import pathlib
import logging
import warnings


# region Settings

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", message=".*per_message.*")

# endregion
# region Constants

# Состояния для FSM
GET_FULL_NAME, GET_PHONE, AGREE_TO_OFFER = range(3)

# Путь к документу с офертой
OFFER_PATH = pathlib.Path(__file__).parent / "Оферта.pdf"

# endregion
# region Def



# Обрабатывает начало работы пользователя с ботом
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    try:
        with Session() as session:
            db_user = session.query(User).filter_by(telegram_id=user_id).first()
            
            if not db_user:
                await update.message.reply_text("👋 Добро пожаловать! Введите ваше ФИО:")
                return GET_FULL_NAME

            elif not db_user.agreed_to_offer:
                await send_offer(chat_id, context)
                return AGREE_TO_OFFER

            else:
                await update.message.reply_text("🔁 Вы уже зарегистрированы!")
                await show_main_menu(chat_id, context)
                return ConversationHandler.END

    except Exception as e:
        logger.error(f"Ошибка в start: {e}")
        await update.message.reply_text("⚠️ Произошла ошибка. Пожалуйста, попробуйте позже.")
        return ConversationHandler.END
        


# Запрашивает ФИО у пользователя
async def get_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['full_name'] = update.message.text
        
        keyboard = [[KeyboardButton("📱 Отправить номер", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        await update.message.reply_text(
            "Теперь отправьте ваш номер телефона:",
            reply_markup=reply_markup
        )
        return GET_PHONE

    except Exception as e:
        logger.error(f"Ошибка в get_full_name: {e}")
        await update.message.reply_text("⚠️ Произошла ошибка. Пожалуйста, попробуйте снова.")
        return ConversationHandler.END



# Запрашивает номер телефона у пользователя
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not hasattr(update.message, 'contact'):
            await update.message.reply_text("Пожалуйста, отправьте номер телефона через кнопку")
            return GET_PHONE
            
        phone = update.message.contact.phone_number
        context.user_data['phone'] = phone
        
        with Session() as session:
            new_user = User(
                telegram_id=update.effective_user.id,
                full_name=context.user_data['full_name'],
                phone=phone
            )
            session.add(new_user)
            session.commit()
        
        await update.message.reply_text(
            "Спасибо! Теперь отправляем оферту...",
            reply_markup=ReplyKeyboardRemove()
        )
        
        await send_offer(update.effective_chat.id, context)
        return AGREE_TO_OFFER

    except Exception as e:
        logger.error(f"Ошибка в get_phone: {e}")
        await update.message.reply_text("⚠️ Произошла ошибка. Пожалуйста, начните снова с /start")
        return ConversationHandler.END



# Отправляет оферту пользователю
async def send_offer(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    try:
        keyboard = [[InlineKeyboardButton("✅ Согласен", callback_data="agree_offer")]]
        with open(OFFER_PATH, 'rb') as file:
            await context.bot.send_document(
                chat_id=chat_id,
                document=file,
                caption="📄 Пожалуйста, ознакомьтесь с офертой:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    except Exception as e:
        logger.error(f"Ошибка отправки оферты: {e}")
        await context.bot.send_message(chat_id, "⚠️ Не удалось отправить оферту")



# Обрабатывает согласие с офертой
async def agree_to_offer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        user_id = query.from_user.id
        chat_id = query.message.chat_id if query.message else None
        
        if not chat_id:
            logger.error(f"Не удалось определить chat_id для пользователя {user_id}")
            return ConversationHandler.END

        with Session() as session:
            user = session.query(User).filter_by(telegram_id=user_id).first()
                
            if not user:
                logger.error(f"Пользователь {user_id} не найден в БД")
                try:
                    await query.edit_message_text("⚠️ Ошибка: пользователь не найден")
                except Exception as e:
                    logger.error(f"Не удалось отредактировать сообщение: {e}")
                return AGREE_TO_OFFER

            if user.agreed_to_offer:
                logger.info(f"Пользователь {user_id} уже принял оферту ранее")
                try:
                    await query.answer("Вы уже приняли оферту ранее", show_alert=True)
                    await show_main_menu(chat_id, context)
                except telegram.error.BadRequest as e:
                    if "Chat not found" in str(e):
                        logger.warning(f"Чат {chat_id} не найден, возможно пользователь заблокировал бота")
                return ConversationHandler.END

            user.agreed_to_offer = True
            session.commit()
                    
            try:
                # Пытаемся обновить исходное сообщение с офертой
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception as e:
                logger.warning(f"Не удалось обновить разметку сообщения: {e}")

            try:
                # Отправляем подтверждение
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="✅ Спасибо! Теперь вам доступен функционал бота."
                )
                await show_main_menu(chat_id, context)

            except telegram.error.BadRequest as e:
                if "Chat not found" in str(e):
                    logger.warning(f"Не удалось отправить сообщение: чат {chat_id} не найден")
                    return ConversationHandler.END
                raise

            return ConversationHandler.END
            
    except Exception as e:
        logger.error(f"Ошибка в agree_to_offer: {e}")

        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Произошла ошибка. Пожалуйста, попробуйте снова."
        )
        return AGREE_TO_OFFER



# Отображает пункты главного меню
async def show_main_menu(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    print(f"{WEBAPP_URL}/schedule")
    keyboard = [
        [InlineKeyboardButton("📱 Открыть приложение", web_app=WebAppInfo(url=f"{WEBAPP_URL}"))],
        [InlineKeyboardButton("📅 Расписание", web_app=WebAppInfo(url=f"{WEBAPP_URL}/schedule"))],
        [InlineKeyboardButton("💳 Мои абонементы", web_app=WebAppInfo(url=f"{WEBAPP_URL}/subscriptions"))],
        [InlineKeyboardButton("📝 Мои записи", web_app=WebAppInfo(url=f"{WEBAPP_URL}/bookings"))]
    ]

    await context.bot.send_message(
        chat_id=chat_id,
        text="🏠 Главное меню:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )



# Основной инициализирующий метод
def main():
    if not WEBAPP_URL:
        raise ValueError("WEBAPP_URL не задан в config.py")
    if not OFFER_PATH.exists():
        logger.error(f"Файл оферты не найден: {OFFER_PATH}")
        raise FileNotFoundError("Файл оферты отсутствует")

    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Проверка заблокированных пользователей
        application.job_queue.run_once(check_blocked_users, when=5)
        
        # Обработчик ошибок
        application.add_error_handler(error_handler)
        
        # Обработчик событий блокировки/разблокировки
        application.add_handler(ChatMemberHandler(
            handle_chat_member_update,
            chat_member_types=ChatMemberHandler.MY_CHAT_MEMBER  # Обрабатываем только изменения статуса бота
        ))

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                GET_FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_full_name)],
                GET_PHONE: [MessageHandler(filters.CONTACT, get_phone)],
                AGREE_TO_OFFER: [CallbackQueryHandler(agree_to_offer, pattern="^agree_offer$")]
            },
            fallbacks=[],
            allow_reentry=True,
            per_chat=True,  # Разрешить только один активный диалог в чате
            per_user=True   # Разрешить только один активный диалог для пользователя
        )
        
        application.add_handler(conv_handler)
        
        # Обработчик непредвиденных сообщений от пользователя
        application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_unknown_message))
        
        try:
            application.run_polling()
        except telegram.error.Conflict as e:
            logger.error(f"Ошибка: {e}\nЗакройте другие экземпляры бота и попробуйте снова")
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}")

    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        


# Обрабатывает блокировку/разблокировку бота пользователем
async def handle_chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Проверяем, что это обновление статуса чата
        if not update.my_chat_member:
            logger.debug("Получен update без my_chat_member, пропускаем")
            return

        # Проверяем, что изменение касается нашего бота
        if update.my_chat_member.new_chat_member.user.id != context.bot.id:
            return

        # Только приватные чаты
        if update.my_chat_member.chat.type != "private":
            return

        old_status = update.my_chat_member.old_chat_member.status
        new_status = update.my_chat_member.new_chat_member.status
        user_id = update.my_chat_member.from_user.id

        logger.info(f"Статус бота изменился: {old_status} -> {new_status} для пользователя {user_id}")

        with Session() as session:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                return

            # Обработка блокировки
            if new_status == ChatMemberStatus.BANNED:  # Используем BANNED вместо LEFT
                user.agreed_to_offer = False
                session.commit()
                logger.info(f"Пользователь {user_id} заблокировал бота, сброшен флаг agreed_to_offer")

            # Обработка разблокировки
            elif old_status == ChatMemberStatus.BANNED and new_status == ChatMemberStatus.MEMBER:
                await context.bot.send_message(
                    chat_id=update.my_chat_member.chat.id,
                    text="Спасибо за разблокировку! Для продолжения работы необходимо подтвердить согласие с офертой!"
                )
                logger.info(f"Пользователь {user_id} разблокировал бота, отправлена оферта")

    except Exception as e:
        logger.error(f"Ошибка в обработчике статуса: {e}", exc_info=True)


# Проверяет заблокированных пользователей и выставляет им флаг необходимости принять оферту
async def check_blocked_users(context: ContextTypes.DEFAULT_TYPE):
    with Session() as session:
        users = session.query(User).filter_by(agreed_to_offer=True).all()
        for user in users:
            try:
                await context.bot.get_chat_member(user.telegram_id, context.bot.id)
            except telegram.error.Forbidden:
                user.agreed_to_offer = False
                session.commit()
                logger.info(f"Обнаружен заблокированный пользователь: {user.telegram_id}")



# Обрабатывает ошибки
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}")
    
    error = context.error
    
    # Ловим ошибку "Forbidden: bot was blocked by the user"
    if isinstance(error, telegram.error.Forbidden) and "blocked" in str(error):
        user_id = None
        if update and update.effective_user:
            user_id = update.effective_user.id
        elif update and update.callback_query:
            user_id = update.callback_query.from_user.id
            
        if user_id:
            with Session() as session:
                user = session.query(User).filter_by(telegram_id=user_id).first()
                if user:
                    user.agreed_to_offer = False
                    session.commit()
                    logger.info(f"Пользователь {user_id} заблокировал бота (обнаружено через Forbidden)")
    
    try:
        if update is None:
            return
        
        chat_id = None
        if hasattr(update, 'message') and update.message:
            chat_id = update.message.chat_id
        elif hasattr(update, 'callback_query') and update.callback_query:
            chat_id = update.callback_query.message.chat_id
            
        if chat_id:
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ Произошла ошибка. Пожалуйста, попробуйте снова."
            )
    except Exception as e:
        logger.error(f"Ошибка в error_handler: {e}")
       
       
       
# Обрабатывает непредвиденные сообщения от пользователя
async def handle_unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📱 Открыть приложение", web_app=WebAppInfo(url=f"{WEBAPP_URL}"))]
    ]
    
    await update.message.reply_text(
        "🤖 Воспользуйтесь кнопкой ниже для открытия приложения или введите команду:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )



# endregion
# region Start Bot



# Запуск бота
if __name__ == "__main__":
    main()
    
    
    
# endregion
