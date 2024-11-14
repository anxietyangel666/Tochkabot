from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from utils.states import *
import logging

logger = logging.getLogger('TelegramBot')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.debug(f"Вызвана команда start пользователем {update.effective_user.id}")
    try:
        keyboard = [
            [KeyboardButton("🔐 Регистрация"),
             KeyboardButton("🔑 Авторизация")],
            [KeyboardButton("🏪 Регистрация магазина"),
             KeyboardButton("🏪 Авторизоваться в магазин")]
        ]
        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )
        await update.message.reply_text(
            'Добро пожаловать! Выберите действие:',
            reply_markup=reply_markup
        )
        logger.debug("Отправлено стартовое меню")
        return LOGIN
    except Exception as e:
        logger.error(f"Ошибка в функции start: {e}")
        logger.exception(e)
        raise

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.debug(f"Вызвана команда cancel пользователем {update.effective_user.id}")
    await update.message.reply_text('Операция отменена.')
    return ConversationHandler.END

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.debug(f"Пользователь {update.effective_user.id} вышел из системы")
    return await start(update, context) 