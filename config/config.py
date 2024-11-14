from dotenv import load_dotenv
import os
import logging

logger = logging.getLogger('TelegramBot')

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    logger.error("Не найден токен бота в переменных окружения!")
    raise ValueError("BOT_TOKEN не установлен в .env файле")

logger.info(f"Загружена конфигурация, токен бота: {BOT_TOKEN[:10]}...")

DATABASE_NAME = 'users.db' 