from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from telegram.error import TelegramError
from config.config import BOT_TOKEN
from database.db_handler import DatabaseHandler
from handlers.auth_handler import AuthHandler
from handlers.common_handler import start, cancel, logout
from utils.states import *
from utils.logger import setup_logger
import os
import sys
import asyncio

# Создаем директорию для логов, если её нет
os.makedirs('logs', exist_ok=True)

# Инициализируем логгер
logger = setup_logger()

async def error_handler(update, context):
    """Обработчик ошибок"""
    logger.error(f"Произошла ошибка: {context.error}")
    logger.exception(context.error)

def main():
    try:
        logger.info("Запуск бота...")
        
        # Инициализация базы данных
        db = DatabaseHandler('users.db')
        db.setup_database()
        logger.info("База данных инициализирована")
        
        # Инициализация обработчика авторизации
        auth_handler = AuthHandler()
        
        # Создаем приложение
        application = Application.builder().token(BOT_TOKEN).build()
        logger.info(f"Приложение создано с токеном: {BOT_TOKEN[:10]}...")

        # Добавляем обработчик ошибок
        application.add_error_handler(error_handler)

        # Создаем ConversationHandler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                LOGIN: [
                    MessageHandler(filters.Regex('^🔐 Регистрация$'), auth_handler.register),
                    MessageHandler(filters.Regex('^🔑 Авторизация$'), auth_handler.authorize),
                    MessageHandler(filters.Regex('^🏪 Регистрация магазина$'), auth_handler.start_add_store),
                    MessageHandler(filters.Regex('^🏪 Авторизоваться в магазин$'), auth_handler.start_store_auth),
                    MessageHandler(filters.Regex('^↩️ В главное меню$'), start),
                    MessageHandler(filters.Regex('^↩️ Назад$'), start),
                ],
                STORE_AUTH: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler.handle_store_auth)
                ],
                STORE_ADDRESS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler.get_store_address)
                ],
                FULL_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler.get_full_name)
                ],
                BARCODE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler.get_barcode)
                ],
                BARCODE_AUTH: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler.check_auth_barcode)
                ],
                MENU: [
                    MessageHandler(filters.Regex('^✏️ Редактировать профиль$'), auth_handler.show_edit_menu),
                    MessageHandler(filters.Regex('^🔐 Получить права админа$'), auth_handler.request_admin_rights),
                    MessageHandler(filters.Regex('^👑 Админ-панель$'), auth_handler.show_admin_panel),
                    MessageHandler(filters.Regex('^🚪 Выйти$'), logout),
                    MessageHandler(filters.Regex('^📅 График$'), auth_handler.show_schedule_menu),
                ],
                ADMIN_CODE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler.check_admin_code)
                ],
                EDIT_CHOICE: [
                    MessageHandler(filters.Regex('^📝 Изменить ФИО$'), auth_handler.edit_name),
                    MessageHandler(filters.Regex('^🔢 Изменить штрих-код$'), auth_handler.edit_barcode),
                    MessageHandler(filters.Regex('^📅 Указать дату трудоустройства$'), auth_handler.edit_hire_date),
                    MessageHandler(filters.Regex('^🏪 Выбрать магазин$'), auth_handler.show_stores_list),
                    MessageHandler(filters.Regex('^↩️ Назад$'), auth_handler.show_menu),
                ],
                SELECT_STORE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler.handle_store_selection)
                ],
                EDIT_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler.save_new_name)
                ],
                EDIT_BARCODE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler.save_new_barcode)
                ],
                EDIT_HIRE_DATE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler.save_hire_date)
                ],
                ADMIN_MENU: [
                    MessageHandler(filters.Regex('^👥 Управление сотрудниками$'), auth_handler.show_users_list),
                    MessageHandler(filters.Regex('^🏪 Управление магазинами$'), auth_handler.show_stores_menu),
                    MessageHandler(filters.Regex('^👨‍💼 Управление администраторами$'), auth_handler.show_administrators),
                    MessageHandler(filters.Regex('^↩️ Назад$'), auth_handler.show_menu),
                ],
                STORES_MENU: [
                    MessageHandler(filters.Regex('^➕ Добавить магазин$'), auth_handler.start_add_store),
                    MessageHandler(filters.Regex('^❌ Удалить магазин$'), auth_handler.delete_store_start),
                    MessageHandler(filters.Regex('^👥 Сотрудники магазина$'), auth_handler.show_store_employees),
                    MessageHandler(filters.Regex('^↩️ Назад$'), auth_handler.show_admin_panel),
                ],
                DELETE_STORE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler.handle_store_deletion)
                ],
                SELECT_STORE_EMPLOYEES: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler.show_employees_list)
                ],
                SELECT_EMPLOYEE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler.handle_employee_selection)
                ],
                EMPLOYEE_ACTIONS: [
                    MessageHandler(filters.Regex('^❌ Удалить сотрудника$'), auth_handler.delete_employee),
                    MessageHandler(filters.Regex('^🏪 Указать магазин$'), auth_handler.show_stores_list),
                    MessageHandler(filters.Regex('^↩️ Назад$'), auth_handler.show_employees_list),
                ],
                SELECT_ADMIN: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler.handle_admin_selection)
                ],
                ASSIGN_STORES: [
                    MessageHandler(filters.Regex('^🏪 Прикрепить магазины$'), auth_handler.show_stores_for_assignment),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler.handle_store_assignment)
                ],
                SELECT_USER: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler.handle_user_selection)
                ],
                SELECT_POSITION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler.handle_position_selection)
                ],
                EDIT_STORE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler.handle_store_edit)
                ],
                USER_MANAGEMENT: [
                    MessageHandler(filters.Regex('^👔 Изменить должность$'), auth_handler.show_position_selection),
                    MessageHandler(filters.Regex('^🏪 Изменить магазин$'), auth_handler.show_store_selection),
                    MessageHandler(filters.Regex('^❌ Удалить админ права$'), auth_handler.remove_admin_rights),
                    MessageHandler(filters.Regex('^↩️ Назад$'), auth_handler.show_users_list),
                ],
                SCHEDULE_MENU: [
                    MessageHandler(filters.Regex('^👁 Посмотреть график$'), auth_handler.view_schedule),
                    MessageHandler(filters.Regex('^✏️ Редактировать график$'), auth_handler.edit_schedule),
                    MessageHandler(filters.Regex('^➕ Создать график$'), auth_handler.create_schedule),
                    MessageHandler(filters.Regex('^🔄 Добавить подмену$'), auth_handler.start_add_substitution),
                    MessageHandler(filters.Regex('^📝 Редактировать подмену$'), auth_handler.edit_substitution_menu),
                    MessageHandler(filters.Regex('^↩️ Назад$'), auth_handler.show_menu),
                ],
                CREATE_SCHEDULE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler.save_schedule),
                ],
                EDIT_SCHEDULE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler.save_schedule),
                ],
                VIEW_SCHEDULE: [
                    MessageHandler(filters.Regex('^↩️ Назад$'), auth_handler.show_schedule_menu),
                ],
                ADD_SUBSTITUTION_STORE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler.handle_substitution_store),
                ],
                ADD_SUBSTITUTION_DATE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler.handle_substitution_date),
                ],
                ADD_SUBSTITUTION_HOURS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler.handle_substitution_hours),
                ],
                EDIT_SUBSTITUTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler.handle_substitution_edit_choice)
                ],
                SELECT_SUBSTITUTION_DATE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler.handle_substitution_date_selection)
                ],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
            allow_reentry=True,
            name='main_conversation'
        )

        logger.info("Добавление обработчика конверсации")
        application.add_handler(conv_handler)
        
        # Запускаем бота
        logger.info("Запуск процесса поллинга")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")
        logger.exception(e)
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        logger.exception(e) 