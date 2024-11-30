from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.db_handler import DatabaseHandler
from config.config import DATABASE_NAME
from utils.states import *
from handlers.common_handler import start
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar

logger = logging.getLogger('TelegramBot')

ADMIN_SECRET_CODE = "748596"

POSITIONS = {
    "1": "Кассир Торгового Зала",
    "2": "Администратор",
    "3": "КРО",
    "4": "Территориальный менеджер",
    "5": "Служба Безопасности"
}

class AuthHandler:
    def __init__(self):
        self.db = DatabaseHandler(DATABASE_NAME)
        logger.info("AuthHandler инициализирован")

    def calculate_experience(self, hire_date_str: str) -> str:
        """Расчет стажа работы"""
        if not hire_date_str:
            return "Дата не указана"
        
        try:
            hire_date = datetime.strptime(hire_date_str, '%d.%m.%Y')
            today = datetime.now()
            diff = relativedelta(today, hire_date)
            
            years = diff.years
            months = diff.months
            
            if years > 0:
                if months > 0:
                    return f"{years} г. {months} мес."
                return f"{years} г."
            elif months > 0:
                return f"{months} мес."
            else:
                return "Менее месяца"
        except ValueError:
            return "Ошибка в формате даты"

    async def format_profile_info(self, user_data, user_id):
        """Форматирование информации профиля"""
        full_name, barcode, hire_date, position, is_admin, work_store_id, store_address = user_data
        
        # Базовая информация, общая для всех
        profile_text = [
            f"Ваше ФИО: {full_name}",
            f"Должность: {position}",
            f"Ваш штрих-код: {barcode}"
        ]
        
        # Добавляем информацию о магазине только для определенных должностей
        if position in ["Кассир Торгового Зала", "Администратор"]:
            store_text = store_address if store_address else "Не указан"
            profile_text.append(f"Магазин: {store_text}")
        
        # Добавляем информацию о дате трудоустройства и стаже
        if hire_date:
            profile_text.append(f"Дата трудоустройства: {hire_date}")
            # Вычисление стажа работы
            hire_datetime = datetime.strptime(hire_date, '%d.%m.%Y')
            experience = relativedelta(datetime.now(), hire_datetime)
            experience_text = f"{experience.years} г. {experience.months} мес."
            profile_text.append(f"Стаж работы: {experience_text}")
        else:
            profile_text.extend([
                "Дата трудоустройства: Не указана",
                "Стаж работы: Дата трудоустройства не указана"
            ])
        
        # Добавляем информацию о прикрепленных магазинах только для Администраторов
        if position == "Администратор":
            admin_stores = self.db.get_admin_stores(user_id)
            if admin_stores:
                stores_text = ", ".join([store[2] for store in admin_stores])
                profile_text.append(f"Прикрепленные магазины: {stores_text}")
            else:
                profile_text.append("Прикрепленные магазины: Не назначены")
        
        return "\n".join(profile_text)

    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать главное меню"""
        user_id = context.user_data.get('user_id')
        user_data = self.db.get_user_data(user_id)
        
        if not user_data:
            await update.message.reply_text("Ошибка: данные пользователя не найдены")
            return LOGIN

        # Распаковываем все значения из user_data
        full_name, barcode, hire_date, position, is_admin, work_store_id, store_address = user_data
        
        # Формируем клавиатуру в зависимости от прав пользователя
        keyboard = [
            ['✏️ Редактировать профиль']
        ]

        # Сываем кнопку рафик для определенных должностей
        if position not in ['КРО', 'Территориальный менеджер', 'Служба безопасности']:
            keyboard.append(['📅 График'])

        # Территориальный менеджер всегда должен иметь доступ к админ-панели
        if position == 'Территориальный менеджер' or is_admin:
            keyboard.append(['👑 Админ-панель'])
        elif not is_admin:
            keyboard.append(['🔐 Получить права админа'])
        
        keyboard.append(['🚪 Выйти'])
        
        # Форматируем текст профиля
        profile_text = await self.format_profile_info(user_data, user_id)
        
        await update.message.reply_text(
            profile_text,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return MENU

    async def show_edit_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню редктирования профиля"""
        user_id = context.user_data.get('user_id')
        user_data = self.db.get_user_data(user_id)
        
        if not user_data:
            await update.message.reply_text("Ошибка: данные пользователя не найдены")
            return await self.show_menu(update, context)

        _, _, _, position, _, _, _ = user_data
        
        keyboard = [
            ['📝 Изменить ФИО'],
            ['🔢 Изменить штрих-код'],
            ['📅 Указать дату трудоустройства']
        ]
        
        # Добавляем кнопку выбора магазина только для определенных должностей
        if position not in ['КРО', 'Территориальный менеджер', 'Служба безопасности']:
            keyboard.append(['🏪 Выбрать магазин'])
        
        keyboard.append(['↩️ Назад'])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            'Выберите, что хотите изменить:',
            reply_markup=reply_markup
        )
        return EDIT_CHOICE


    async def edit_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать процесс изменения имени"""
        reply_keyboard = [['↩️ Назад']]
        await update.message.reply_text(
            'Введите новое ФИО:',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return EDIT_NAME

    async def save_new_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сохранить новое имя"""
        if update.message.text == '↩️ Назад':
            return await self.show_edit_menu(update, context)

        new_name = update.message.text
        user_id = context.user_data.get('user_id')
        self.db.update_user_name(user_id, new_name)
        
        return await self.show_menu(update, context)

    async def edit_barcode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать процесс изменения штрих-кода"""
        reply_keyboard = [['↩️ Назад']]
        await update.message.reply_text(
            'Отсканируйте или введите новый штрих-код:',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return EDIT_BARCODE

    async def save_new_barcode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сохранить новый штрих-код"""
        if update.message.text == '↩️ Назад':
            return await self.show_edit_menu(update, context)

        new_barcode = update.message.text
        user_id = context.user_data.get('user_id')
        
        # Проверяем, не занят ли штрих-код другим пользователем
        existing_user = self.db.get_user_by_barcode(new_barcode)
        if existing_user and existing_user[0] != user_id:
            await update.message.reply_text('Этот штрих-код уже испоеся другим пользователем!')
            return await self.edit_barcode(update, context)

        self.db.update_user_barcode(user_id, new_barcode)
        return await self.show_menu(update, context)

    async def register(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.debug(f"Начало регистрации для пользователя {update.effective_user.id}")
        reply_keyboard = [['↩️ Назад']]
        await update.message.reply_text(
            'Пожалуйста, введите ваше ФИО:',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return FULL_NAME

    async def get_full_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.debug(f"Получено ФИО: {update.message.text}")
        if update.message.text == '↩️ Назад':
            return await start(update, context)
            
        context.user_data['full_name'] = update.message.text
        reply_keyboard = [['↩️ Назад']]
        await update.message.reply_text(
            'Теперь отсканируйте или введте ваш штрих-код:',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return BARCODE

    async def get_barcode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка штрих-кода при регистрации"""
        if update.message.text == '↩️ Назад':
            return await self.register(update, context)
        
        barcode = update.message.text
        logger.debug(f"Получен штрих-код: {barcode}")
        
        # Проверяем, существует ли штрих-код в базе
        existing_user = self.db.get_user_by_barcode(barcode)
        if existing_user:
            reply_keyboard = [['🔐 Регистрация', '🔑 Авторизация']]
            await update.message.reply_text(
                'Этот штрих-код уже зарегистрирован!\n'
                'Пожалуйста, используйте другой штрих-код или авторизуйтесь.',
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
            )
            return LOGIN

        # Сохраняем штрих-код в контекст
        context.user_data['barcode'] = barcode
        return await self.show_stores_list(update, context)

    async def authorize(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало процесса авторизации"""
        reply_keyboard = [['↩️ Назад']]
        await update.message.reply_text(
            'Пожалуйста, отсканируйте или введите ваш штрих-код:',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return BARCODE_AUTH  # Новое состояние специально для авторизации

    async def check_auth_barcode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Проверка штрих-коа при авторизации"""
        if update.message.text == '↩️ Назад':
            return await self.authorize(update, context)
        
        barcode = update.message.text
        user_data = self.db.get_user_by_barcode(barcode)
        
        if not user_data:
            await update.message.reply_text(
                'Пользователь с таким штрих-кодом не найден.\n'
                'Попробуйте еще раз или зарегистрируйтесь:'
            )
            return BARCODE_AUTH
        
        # Сохраняем ID пользователя в контекст
        user_id = user_data[0]
        context.user_data['user_id'] = user_id
        
        # Получаем полные данные пользователя
        full_user_data = self.db.get_user_data(user_id)
        if full_user_data:
            _, _, _, position, is_admin, _, _ = full_user_data
            # Если пользоатель Территориальный менеджер, автоматически даем права админа
            if position == 'Территориальный менеджер':
                self.db.set_admin_status(user_id, True)
        
        return await self.show_menu(update, context)

    async def edit_hire_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать процесс изменения даты трудоустройства"""
        reply_keyboard = [['↩️ Назад']]
        await update.message.reply_text(
            'Введите дат трудоустройства в формате ДД.ММ.ГГГГ\n'
            'Например: 15.03.2023',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return EDIT_HIRE_DATE

    async def save_hire_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сохранить дату трудоустройства"""
        if update.message.text == '↩️ Назад':
            return await self.show_edit_menu(update, context)

        hire_date = update.message.text
        try:
            # Проверяем корректность формата даты
            datetime.strptime(hire_date, '%d.%m.%Y')
            
            user_id = context.user_data.get('user_id')
            self.db.update_hire_date(user_id, hire_date)
            
            return await self.show_menu(update, context)
        except ValueError:
            await update.message.reply_text(
                'Неверный формат даы! Пожалуйста, используйте формат ДД.ММ.ГГГГ\n'
                'Например: 15.03.2023'
            )
            return EDIT_HIRE_DATE

    async def request_admin_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запрос секретного кода для получения прав админа"""
        reply_keyboard = [['↩️ Назад']]
        await update.message.reply_text(
            'Введите секретный код для получения прав администртора:',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return ADMIN_CODE

    async def check_admin_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Проверка секретного кода"""
        if update.message.text == '↩️ Назад':
            return await self.show_menu(update, context)
            
        if update.message.text == ADMIN_SECRET_CODE:
            user_id = context.user_data.get('user_id')
            self.db.set_admin_status(user_id, True)
            
            await update.message.reply_text(
                '🎉 Поздравляем! Вы получили права администратоа!'
            )
            return await self.show_menu(update, context)
        else:
            await update.message.reply_text(
                '❌ Неверный код! Попробуйте еще раз или вернитесь назад.',
                reply_markup=ReplyKeyboardMarkup([['↩️ Нзд']], one_time_keyboard=True)
            )
            return ADMIN_CODE

    async def show_admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать панель администратора"""
        keyboard = [
            ['👥 Управление сотрудниками'],
            ['🏪 Управление магазинами'],
            ['👨‍💼 Управление администраторами'],
            ['↩️ Назад']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            'Панель администратора:',
            reply_markup=reply_markup
        )
        return ADMIN_MENU

    async def show_users_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список пользователей"""
        if update.message.text == '↩️ Назад':
            return await self.show_menu(update, context)

        users = self.db.get_all_users()
        users_list = ""
        for i, user in enumerate(users, 1):
            users_list += f"{i}. {user[1]} ({user[5]})\n"

        await update.message.reply_text(
            f"Список сотрудников:\n\n{users_list}\n"
            "Введите номер сотрудника для редактирования:"
        )
        context.user_data['users_list'] = users
        return SELECT_USER

    async def handle_user_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора пльзователя"""
        if update.message.text == '↩️ Назад':
            return await self.show_admin_panel(update, context)

        try:
            selected_index = int(update.message.text) - 1
            users_list = context.user_data.get('users_list', [])
            
            if 0 <= selected_index < len(users_list):
                selected_user = users_list[selected_index]
                context.user_data['selected_user_id'] = selected_user[0]
                return await self.show_user_management(update, context)
            else:
                await update.message.reply_text("Неверный номер сотрудника. Попробуйте еще раз:")
                return SELECT_USER
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите число.")
            return SELECT_USER

    async def handle_position_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора должности"""
        if update.message.text == '↩️ Назад':
            return await self.show_users_list(update, context)

        position_number = update.message.text
        if position_number in POSITIONS:
            user_id = context.user_data['selected_user_id']
            new_position = POSITIONS[position_number]
            
            # Обновляем должность (все права и статусы обновляются внутри метода)
            self.db.update_user_position(user_id, new_position)
            
            await update.message.reply_text(
                f"Должность успешно обновлена на: {new_position}"
            )
            
            return await self.show_users_list(update, context)
        else:
            await update.message.reply_text(
                "Неверный номер должности. Пожалуйста, выберите из списка:"
                "\n1 - Кассир Торгового Зала"
                "\n2 - Администратор"
                "\n3 - КРО"
                "\n4 - Территориальный менеджер"
                "\n5 - Служба Бзопасности"
            )
            return SELECT_POSITION

    async def start_add_store(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало процесса добавления магазина"""
        await update.message.reply_text(
            'Введите адрес магазина:',
            reply_markup=ReplyKeyboardMarkup([['↩️ Назад']], resize_keyboard=True)
        )
        return STORE_ADDRESS

    async def get_store_address(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение адреса магазина и создание магазина"""
        if update.message.text == '↩️ Назад':
            return await start(update, context)
        
        address = update.message.text
        store_id = self.db.add_store(address)
        
        if store_id:
            store = self.db.get_store_by_id(store_id)
            employees_count = self.db.get_store_employees_count(store_id)
            
            profile_text = (
                f"✅ Магазин успешно создан!\n\n"
                f"🏪 Профиль магазина:\n"
                f"ID: {store[0]}\n"
                f"Нмер магазина: {store[1]}\n"
                f"Адрес: {store[2]}\n"
                f"👥 Количество сотрудников: {employees_count}"
            )
            
            await update.message.reply_text(
                profile_text,
                reply_markup=ReplyKeyboardMarkup([['️ В главное меню']], resize_keyboard=True)
            )
            return LOGIN
        else:
            await update.message.reply_text(
                "❌ Ошибка при создании магазина. Попробуйте еще раз."
            )
            return await start(update, context)

    async def show_administrators(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список администраторов"""
        admins = self.db.get_administrators()
        admins_list = ""
        for i, admin in enumerate(admins, 1):
            admin_id, name = admin
            stores = self.db.get_admin_stores(admin_id)
            stores_text = ", ".join([store[1] for store in stores]) if stores else "Не назначены"
            admins_list += f"{i}. {name} (Магазины: {stores_text})\n"

        await update.message.reply_text(
            f"Список администраоров:\n\n{admins_list}\n"
            "Введите номер администратора для управления:"
        )
        context.user_data['admins_list'] = admins
        return SELECT_ADMIN

    async def handle_admin_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора администратора"""
        if update.message.text == '↩️ Назад':
            return await self.show_admin_panel(update, context)

        try:
            selected_index = int(update.message.text) - 1
            admins_list = context.user_data.get('admins_list', [])
            
            if 0 <= selected_index < len(admins_list):
                selected_admin = admins_list[selected_index]
                context.user_data['selected_admin_id'] = selected_admin[0]
                
                keyboard = [['🏪 Прикрепить магазины'], ['↩️ Назад']]
                await update.message.reply_text(
                    f"Выбран администратор: {selected_admin[1]}\n"
                    "Выберите действие:",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
                return ASSIGN_STORES
            else:
                await update.message.reply_text("Неверный номер администратора. Попробуйте еще раз:")
                return SELECT_ADMIN
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите число.")
            return SELECT_ADMIN

    async def show_stores_for_assignment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список магазинов для прикрепления"""
        stores = self.db.get_all_stores()
        stores_list = "\n".join([f"{store[0]}. {store[2]}" for store in stores])
        
        await update.message.reply_text(
            f"Список магазинов:\n\n{stores_list}\n\n"
            "Введите номера магазинов через запятую (например: 1,3,5):"
        )
        return ASSIGN_STORES

    async def handle_store_assignment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка прикрепления магазинов"""
        if update.message.text == '↩️ Назад':
            return await self.show_administrators(update, context)

        try:
            store_ids = [int(x.strip()) for x in update.message.text.split(',')]
            admin_id = context.user_data['selected_admin_id']
            
            self.db.assign_stores_to_admin(admin_id, store_ids)
            await update.message.reply_text("Магазины успешно прикреплены к администратору!")
            return await self.show_admin_panel(update, context)
        except ValueError:
            await update.message.reply_text(
                "Пожалуйста, введите номера магазинов через запятую (например: 1,3,5)"
            )

    async def show_stores_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список магазинов"""
        stores = self.db.get_all_stores()
        
        if not stores:
            # Если магазинов нет, пропускаем выбор магазина
            return await self.handle_store_selection(update, context)
        
        stores_list = "\n".join([f"{store[0]}. {store[2]}" for store in stores])
        keyboard = [['⏩ Пропустить'], ['↩️ Назад']]
        
        await update.message.reply_text(
            f"Выберите магазин из списка:\n\n{stores_list}\n\n"
            "Введите номер магазина или нажмите 'Пропустить':",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return SELECT_STORE

    async def handle_store_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора магазина"""
        if update and update.message and update.message.text == '↩️ Назад':
            return await self.show_stores_list(update, context)
        
        store_id = None
        store = None
        
        if update and update.message and update.message.text != '⏩ Пропустить':
            try:
                store_id = int(update.message.text)
                store = self.db.get_store_by_id(store_id)
                if not store:
                    await update.message.reply_text(
                        "Маазин с таким номером не найден. Попробуйте еще раз:"
                    )
                    return SELECT_STORE
            except ValueError:
                await update.message.reply_text(
                    "Пожалуйста, введите номер магазина цифрами."
                )
                return SELECT_STORE

        # Проверяем, существует ли уже пользователь
        user_id = context.user_data.get('user_id')
        if user_id:
            # Обновляем магазин существующего пользователя
            self.db.update_user_store(user_id, store_id)
            return await self.show_menu(update, context)
        else:
            # Создаем нового пользователя (регистрация)
            full_name = context.user_data.get('full_name')
            barcode = context.user_data.get('barcode')
            
            user_id = self.db.add_user(
                telegram_id=update.message.from_user.id,
                full_name=full_name,
                barcode=barcode,
                work_store_id=store_id
            )
            
            context.user_data['user_id'] = user_id
            
            store_text = store[2] if store else "Не указан"
            
            reply_keyboard = [['✏️ Редактировать профиль'], ['🔐 Получить права админа'], ['🚪 Выйти']]
            await update.message.reply_text(
                f'Регистрация успешна!\n'
                f'Добро пожаловать!\n'
                f'Ваше ФИО: {full_name}\n'
                f'Должность: Кассир Торгового Зала\n'
                f'Магазин: {store_text}\n'
                f'Ваш штрих-код: {barcode}\n'
                f'Дата трудоустройства: Не указана\n'
                f'Стаж работы: Дата трудоустройства не казана',
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
            )
            return MENU

    async def show_stores_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню управления магазинами"""
        keyboard = [
            ['➕ Добавить магазин'],
            ['❌ Удалить магазин'],
            ['👥 Сотрудники магазина'],
            ['↩️ Назад']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            'Управление магазинами:',
            reply_markup=reply_markup
        )
        return STORES_MENU

    async def delete_store_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало процесса удаления магазина"""
        stores = self.db.get_all_stores()
        if not stores:
            await update.message.reply_text("В базе нет магазинов.")
            return await self.show_stores_menu(update, context)

        stores_list = "\n".join([f"{store[0]}. {store[1]}" for store in stores])
        keyboard = [['↩️ Назад']]
        await update.message.reply_text(
            f"Список магазинов:\n\n{stores_list}\n\n"
            "Введите номер магазина для удлния:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return DELETE_STORE

    async def handle_store_deletion(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка удаления магазина"""
        if update.message.text == '↩️ Назад':
            return await self.show_stores_menu(update, context)

        try:
            store_id = int(update.message.text)
            store = self.db.get_store_by_id(store_id)
            if store:
                self.db.delete_store(store_id)
                await update.message.reply_text("Магазин успешно удален!")
            else:
                await update.message.reply_text("Магазин с таким номером не найден.")
            return await self.show_stores_menu(update, context)
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите номер магазина цифрами.")
            return DELETE_STORE

    async def show_store_employees(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список магазинов для просмотра сотрудников"""
        stores = self.db.get_all_stores()
        if not stores:
            await update.message.reply_text("В базе нет магазинов.")
            return await self.show_stores_menu(update, context)

        stores_list = "\n".join([f"{store[0]}. {store[2]}" for store in stores])
        keyboard = [['↩️ Назад']]
        await update.message.reply_text(
            f"Выберите магазин для просмотра сотрудников:\n\n{stores_list}\n\n"
            "Введите номер магазина:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return SELECT_STORE_EMPLOYEES

    async def show_employees_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список сотрудников выбранного магазина"""
        if update.message.text == '↩️ Назад':
            return await self.show_stores_menu(update, context)

        try:
            store_id = int(update.message.text)
            store = self.db.get_store_by_id(store_id)
            if not store:
                await update.message.reply_text("Магазин с таким номером не найден.")
                return await self.show_stores_menu(update, context)

            employees = self.db.get_store_employees(store_id)
            if not employees:
                await update.message.reply_text(f"В маазине {store[1]} нет сотрудников.")
                return await self.show_stores_menu(update, context)

            context.user_data['selected_store_id'] = store_id
            context.user_data['store_employees'] = employees

            employees_list = "\n".join([f"{i+1}. {emp[1]} ({emp[2]})" for i, emp in enumerate(employees)])
            keyboard = [['↩️ Назад']]
            await update.message.reply_text(
                f"Сотрудники магазина {store[1]}:\n\n{employees_list}\n\n"
                "Выберите номе сотрудника:",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            return SELECT_EMPLOYEE
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите номер магазина цифрами.")
            return SELECT_STORE_EMPLOYEES

    async def handle_employee_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора сотрудника"""
        if update.message.text == '↩️ Назад':
            return await self.show_store_employees(update, context)

        try:
            employees = context.user_data.get('store_employees', [])
            selected_index = int(update.message.text) - 1

            if 0 <= selected_index < len(employees):
                employee = employees[selected_index]
                context.user_data['selected_employee_id'] = employee[0]

                keyboard = [
                    ['❌ Удалить сотрудника'],
                    ['🏪 Указать магазин'],
                    ['↩️ Назад']
                ]
                await update.message.reply_text(
                    f"Выбран сотрудник: {employee[1]}\n"
                    "Выберите действие:",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
                return EMPLOYEE_ACTIONS
            else:
                await update.message.reply_text("Неверный номер сотрудника.")
                return SELECT_EMPLOYEE
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите номер сотрудника цифрами.")
            return SELECT_EMPLOYEE

    async def delete_employee(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удаление сотрудника из магазина"""
        if update.message.text == '↩️ Назад':
            return await self.show_employees_list(update, context)

        employee_id = context.user_data.get('selected_employee_id')
        if not employee_id:
            await update.message.reply_text("Ошибка: сотрудник не выбран.")
            return await self.show_stores_menu(update, context)

        # Получаем информацию о сотруднике пере удалением
        employee = self.db.get_user_data(employee_id)
        if employee:
            # Обнуляем магазин у сотрудника
            self.db.update_user_store(employee_id, None)
            await update.message.reply_text(
                f"Сотрудник {employee[0]} удален из магазна."
            )
        else:
            await update.message.reply_text("Ошибка: сотрудник не найден.")

        return await self.show_stores_menu(update, context)

    async def reassign_employee_store(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Именение магазина сотрудника"""
        if update.message.text == '↩️ Назад':
            return await self.handle_employee_selection(update, context)

        try:
            store_id = int(update.message.text)
            employee_id = context.user_data.get('selected_employee_id')
            
            if not employee_id:
                await update.message.reply_text("Ошибка: сотрудник не выбран.")
                return await self.show_stores_menu(update, context)

            store = self.db.get_store_by_id(store_id)
            if not store:
                await update.message.reply_text("Магазин с таким номером не найден.")
                return SELECT_STORE

            # Обновляем магазин сотрудика
            self.db.update_user_store(employee_id, store_id)
            await update.message.reply_text(
                f"Магазин сотрудника успешно изменен на: {store[1]}"
            )
            return await self.show_stores_menu(update, context)

        except ValueError:
            await update.message.reply_text(
                "Пожалуйста, введите номер магазина цифрами."
            )
            return SELECT_STORE

    async def request_admin_rights(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запрос на получение прав администратора"""
        return await self.request_admin_code(update, context)

    async def show_stores_for_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список магазинов для редактирования профиля"""
        stores = self.db.get_all_stores()
        
        if not stores:
            await update.message.reply_text("В базе пока нет магазинов.")
            return await self.show_edit_menu(update, context)
        
        stores_list = "\n".join([f"{store[0]}. {store[2]}" for store in stores])
        keyboard = [['↩️ Назад']]
        
        await update.message.reply_text(
            f"Выберите магазин из списка:\n\n{stores_list}\n\n"
            "Введите номер магазина:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return EDIT_STORE

    async def handle_store_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора магазина при редактировании профиля"""
        if update.message.text == '↩️ Назад':
            return await self.show_edit_menu(update, context)

        try:
            store_id = int(update.message.text)
            store = self.db.get_store_by_id(store_id)
            if not store:
                await update.message.reply_text(
                    "Магазин с таким номером не найден. Попробуйте еще раз:"
                )
                return EDIT_STORE

            user_id = context.user_data.get('user_id')
            self.db.update_user_store(user_id, store_id)
            return await self.show_menu(update, context)

        except ValueError:
            await update.message.reply_text(
                "Пожалуйста, введите номер магазина цифрами."
            )
            return EDIT_STORE

    async def edit_store(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать процесс изменения магазина"""
        stores = self.db.get_all_stores()
        
        if not stores:
            await update.message.reply_text("В базе нет магазинов.")
            return await self.show_edit_menu(update, context)
        
        stores_list = "\n".join([f"{store[0]}. {store[2]}" for store in stores])
        keyboard = [['↩️ Назад']]
        
        await update.message.reply_text(
            f"Выберите магазин из списка:\n\n{stores_list}\n\n"
            "Введите номер магазина:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return EDIT_STORE

    async def handle_store_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора магазина при редактироваии профиля"""
        if update.message.text == '↩️ Назад':
            return await self.show_edit_menu(update, context)

        try:
            store_id = int(update.message.text)
            store = self.db.get_store_by_id(store_id)
            if not store:
                await update.message.reply_text(
                    "Магазин с таким номером не найден. Попробуйте еще раз:"
                )
                return EDIT_STORE

            user_id = context.user_data.get('user_id')
            self.db.update_user_store(user_id, store_id)
            return await self.show_menu(update, context)

        except ValueError:
            await update.message.reply_text(
                "Пожалуйста, введите номер магазина цифрами."
            )
            return EDIT_STORE

    async def show_user_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню управления сотрудником"""
        keyboard = [
            ['👔 Изменить должность'],
            ['🏪 Изменить магазин'],
            ['❌ Удалить админ права'],
            ['↩️ Назад']
        ]
        
        user_id = context.user_data.get('selected_user_id')
        user_data = self.db.get_user_data(user_id)
        
        if not user_data:
            await update.message.reply_text("Ошибка: пользователь не найден")
            return await self.show_admin_panel(update, context)
        
        _, _, _, position, is_admin, _, _ = user_data
        
        # Если у пользователя нет прав админа, убираем кнопку удаления прав
        if not is_admin:
            keyboard.pop(2)
        
        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return USER_MANAGEMENT

    async def show_position_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать выбор длжности"""
        if update.message.text == '↩️ Назад':
            return await self.show_user_management(update, context)
        
        positions_text = "\n".join([f"{k}. {v}" for k, v in POSITIONS.items()])
        await update.message.reply_text(
            "Выберите номер новой должности:\n\n" + positions_text,
            reply_markup=ReplyKeyboardMarkup([['↩️ Назад']], resize_keyboard=True)
        )
        return SELECT_POSITION

    async def show_store_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать выбор магазина"""
        if update.message.text == '↩️ Назад':
            return await self.show_user_management(update, context)
        
        stores = self.db.get_all_stores()
        if not stores:
            await update.message.reply_text("В базе нет магазинов")
            return await self.show_user_management(update, context)
        
        stores_list = "\n".join([f"{store[0]}. {store[2]}" for store in stores])
        await update.message.reply_text(
            f"Выберите магазин из списка:\n\n{stores_list}\n\n"
            "Введите номер магазина:",
            reply_markup=ReplyKeyboardMarkup([['↩️ Назад']], resize_keyboard=True)
        )
        return SELECT_STORE

    async def remove_admin_rights(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удаление прав администратора"""
        if update.message.text == '↩️ Назад':
            return await self.show_user_management(update, context)
        
        user_id = context.user_data.get('selected_user_id')
        user_data = self.db.get_user_data(user_id)
        
        if not user_data:
            await update.message.reply_text("Ошибка: пользователь не найден")
            return await self.show_admin_panel(update, context)
        
        _, _, _, position, is_admin, _, _ = user_data
        
        # Проверяем должность пользователя
        if position == 'Территориальный менеджер':
            await update.message.reply_text(
                "❌ Невозможно удалить права администратора у Территориального менеджера.\n"
                "Для удаления прав администратора сначала измение должность пользователя."
            )
            return await self.show_user_management(update, context)
        
        # Убираем права админа
        self.db.set_admin_status(user_id, False)
        await update.message.reply_text("✅ Права администратора успешно удалены")
        return await self.show_user_management(update, context)

    async def start_store_auth(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало процесса авторизации в магазине"""
        await update.message.reply_text(
            'Введите ID магазина:',
            reply_markup=ReplyKeyboardMarkup([['↩️ Назад']], resize_keyboard=True)
        )
        return STORE_AUTH

    async def handle_store_auth(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка авторизации в магазине"""
        if update.message.text == '↩️ Назад':
            return await start(update, context)
        
        try:
            store_id = int(update.message.text)
            store = self.db.get_store_by_id(store_id)
            
            if not store:
                await update.message.reply_text(
                    "❌ Магазин с таким ID не найден. Попробуйте еще раз:"
                )
                return STORE_AUTH
            
            store_id, store_number, address = store
            employees_count = self.db.get_store_employees_count(store_id)
            
            profile_text = (
                f"🏪 Профил�� магазина:\n"
                f"ID: {store_id}\n"
                f"Номер магазина: {store_number}\n"
                f"Адрес: {address}\n"
                f"👥 Количество сотрудников: {employees_count}"
            )
            
            await update.message.reply_text(
                profile_text,
                reply_markup=ReplyKeyboardMarkup([['↩️ В главное меню']], resize_keyboard=True)
            )
            return LOGIN
            
        except ValueError:
            await update.message.reply_text(
                "Пожалуйста, введите ID магазина цифрами."
            )
            return STORE_AUTH

    async def show_schedule_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню графика"""
        keyboard = [
            ['👁 Посмотреть график'],
            ['✏️ Редактировать график'],
            ['➕ Создать график'],
            ['🔄 Добавить подмену'],
            ['📝 Редактировать подмену'],
            ['↩️ Назад']
        ]
        await update.message.reply_text(
            'Меню управления графиком:',
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return SCHEDULE_MENU

    async def view_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Просмотр графика работы"""
        if update.message.text == '↩️ Назад':
            return await self.show_schedule_menu(update, context)
        
        user_id = context.user_data.get('user_id')
        user_data = self.db.get_user_data(user_id)
        
        if not user_data:
            await update.message.reply_text("Ошибка: данные пользователя не найдены")
            return await self.show_menu(update, context)
        
        full_name, _, _, position, _, work_store_id, _ = user_data
        current_month = datetime.now().strftime('%Y-%m')
        
        # Формируем текст с графиком пользователя
        schedule_text = f"📅 График {full_name} на текущий месяц:\n\n"
        schedule = self.db.get_schedule(user_id, work_store_id, current_month)
        
        if schedule:
            schedule_data = schedule
            for i, day in enumerate(schedule_data, 1):
                schedule_text += f"{i:02d}: {'Смена' if day == 'С' else 'Выходной'}\n"
        else:
            schedule_text += "График не найден.\n"
        
        # Добавляем подмены пользователя
        substitutions = self.db.get_user_substitutions(user_id, datetime.now())
        if substitutions:
            schedule_text += "\n🔄 Подмены в этом месяце:\n"
            for date, hours, store in substitutions:
                schedule_text += f"📅 {date}: {hours}ч в {store}\n"
        
        # Получаем коллег из того же магазина
        colleagues = self.db.get_store_employees(work_store_id)
        colleagues_text = ""
        
        if colleagues:
            for colleague_id, colleague_name, colleague_position in colleagues:
                if colleague_id != user_id:  # Пропускаем самого пользователя
                    colleagues_text += f"\n\n👤 {colleague_name} ({colleague_position}):\n"
                    
                    # График коллеги
                    colleague_schedule = self.db.get_schedule(colleague_id, work_store_id, current_month)
                    if colleague_schedule:
                        colleagues_text += "📅 График:\n"
                        for i, day in enumerate(colleague_schedule, 1):
                            colleagues_text += f"{i:02d}: {'Смена' if day == 'С' else 'Выходной'}\n"
                    else:
                        colleagues_text += "График не найден\n"
                    
                    # Подмены коллеги
                    colleague_substitutions = self.db.get_user_substitutions(colleague_id, datetime.now())
                    if colleague_substitutions:
                        colleagues_text += "\n🔄 Подмены:\n"
                        for date, hours, store in colleague_substitutions:
                            colleagues_text += f"📅 {date}: {hours}ч в {store}\n"
        
        # Формируем общий текст
        full_text = schedule_text
        if colleagues_text:
            full_text += "\n\n📋 Графики коллег:" + colleagues_text
        else:
            full_text += "\n\nВ этом магазине нет других сотрудников."
        
        # Отправляем сообщение частями, если оно слишком длинное
        if len(full_text) > 4096:
            for x in range(0, len(full_text), 4096):
                await update.message.reply_text(
                    full_text[x:x+4096],
                    reply_markup=ReplyKeyboardMarkup([['↩️ Назад']], resize_keyboard=True)
                )
        else:
            await update.message.reply_text(
                full_text,
                reply_markup=ReplyKeyboardMarkup([['↩️ Назад']], resize_keyboard=True)
            )
        return SCHEDULE_MENU

    async def create_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создание графика"""
        if update.message.text == '↩️ Назад':
            return await self.show_schedule_menu(update, context)

        current_month = datetime.now()
        days_in_month = calendar.monthrange(current_month.year, current_month.month)[1]
        
        await update.message.reply_text(
            f"Введите дни работы на {current_month.strftime('%B %Y')} "
            f"(всего дней в месяце: {days_in_month})\n"
            "Введите числа рабочих дней через запятую\n"
            "Пример: 1,2,3,7,8,9,13,14,15\n"
            "Все остальные дни будут выходными",
            reply_markup=ReplyKeyboardMarkup([['↩️ Назад']], resize_keyboard=True)
        )
        return CREATE_SCHEDULE

    async def save_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сохранение графика"""
        if update.message.text == '↩️ Назад':
            return await self.show_schedule_menu(update, context)

        try:
            # Получаем введенные пользователем рабочие дни
            work_days = [int(day.strip()) for day in update.message.text.split(',')]
            
            current_month = datetime.now()
            days_in_month = calendar.monthrange(current_month.year, current_month.month)[1]
            
            # Проверяем корректность введенных дней
            if not all(1 <= day <= days_in_month for day in work_days):
                await update.message.reply_text(
                    f"Ошибка: введите числа от 1 до {days_in_month}"
                )
                return CREATE_SCHEDULE
            
            # Создаем график: В - выходной, С - смена
            schedule_data = ['В'] * days_in_month
            for day in work_days:
                schedule_data[day - 1] = 'С'
            
            schedule_string = ''.join(schedule_data)
            current_month_str = datetime.now().strftime('%Y-%m')
            user_id = context.user_data.get('user_id')
            user_data = self.db.get_user_data(user_id)
            
            if not user_data:
                await update.message.reply_text("Ошибка: данные пользователя не найдены")
                return await self.show_menu(update, context)

            _, _, _, _, _, work_store_id, _ = user_data
            
            self.db.save_schedule(user_id, work_store_id, current_month_str, schedule_string)
            
            # Форматируем график для отображения
            formatted_schedule = "\n".join(
                f"{i+1}: {'Смена' if day == 'С' else 'Выходной'}"
                for i, day in enumerate(schedule_data)
            )
            
            await update.message.reply_text(
                f"График успешно сохранен!\n\n"
                f"Ваш график на {current_month.strftime('%B %Y')}:\n"
                f"{formatted_schedule}"
            )
            return await self.show_schedule_menu(update, context)
            
        except ValueError:
            await update.message.reply_text(
                "Ошибка: введите числа через запятую (например: 1,2,3,7,8,9)"
            )
            return CREATE_SCHEDULE

    async def edit_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Редактирование графика"""
        if update.message.text == '↩️ Назад':
            return await self.show_schedule_menu(update, context)

        current_month = datetime.now()
        days_in_month = calendar.monthrange(current_month.year, current_month.month)[1]
        
        await update.message.reply_text(
            f"Введите новый график на {current_month.strftime('%B %Y')} "
            f"({days_in_month} дней)\n"
            "Формат: С-В-С-В... (С - смена, В - выходной)\n"
            "Пример: СССВВСССВВССВ...",
            reply_markup=ReplyKeyboardMarkup([['↩️ Назад']], resize_keyboard=True)
        )
        return EDIT_SCHEDULE

    async def start_add_substitution(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало процесса добавления подмены"""
        if update.message.text == '↩️ Назад':
            return await self.show_schedule_menu(update, context)
        
        stores = self.db.get_all_stores()
        if not stores:
            await update.message.reply_text("В базе нет магазинов")
            return await self.show_schedule_menu(update, context)
        
        stores_list = "\n".join([f"{store[0]}. {store[1]} ({store[2]})" for store in stores])
        await update.message.reply_text(
            f"Выберите магазин для подмены:\n\n{stores_list}\n\n"
            "Введите номер магазина:",
            reply_markup=ReplyKeyboardMarkup([['↩️ Назад']], resize_keyboard=True)
        )
        return ADD_SUBSTITUTION_STORE

    async def handle_substitution_store(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора магазина для подмены"""
        if update.message.text == '↩️ Назад':
            return await self.show_schedule_menu(update, context)
        
        try:
            store_id = int(update.message.text)
            store = self.db.get_store_by_id(store_id)
            
            if not store:
                await update.message.reply_text("Магазин не найден. Попробуйте еще раз:")
                return ADD_SUBSTITUTION_STORE
            
            context.user_data['sub_store_id'] = store_id
            await update.message.reply_text(
                "Введите дату подмены (формат: ДД.ММ.ГГГГ):",
                reply_markup=ReplyKeyboardMarkup([['↩️ Назад']], resize_keyboard=True)
            )
            return ADD_SUBSTITUTION_DATE
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите корректный номер магазина")
            return ADD_SUBSTITUTION_STORE

    async def handle_substitution_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка даты подмены"""
        if update.message.text == '↩️ Назад':
            return await self.start_add_substitution(update, context)
        
        try:
            date = datetime.strptime(update.message.text, '%d.%m.%Y')
            context.user_data['sub_date'] = date.strftime('%Y-%m-%d')
            
            await update.message.reply_text(
                "Введите количество часов:",
                reply_markup=ReplyKeyboardMarkup([['↩️ Назад']], resize_keyboard=True)
            )
            return ADD_SUBSTITUTION_HOURS
        except ValueError:
            await update.message.reply_text("Неверный формат даты. Используйте ДД.ММ.ГГГГ")
            return ADD_SUBSTITUTION_DATE

    async def handle_substitution_hours(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка количества часов подмены"""
        if update.message.text == '↩️ Назад':
            return await self.handle_substitution_store(update, context)
        
        try:
            hours = int(update.message.text)
            if hours <= 0 or hours > 24:
                await update.message.reply_text("Количество часов должно быть от 1 до 24")
                return ADD_SUBSTITUTION_HOURS
            
            user_id = context.user_data.get('user_id')
            
            if context.user_data.get('editing_sub'):
                # Обновляем существующую подмену
                old_date = context.user_data.get('old_sub_date')
                # Получаем текущий store_id для этой подмены
                substitutions = context.user_data.get('substitutions', [])
                selected_index = int(context.user_data.get('selected_sub_index', 0))
                _, _, store = substitutions[selected_index]
                store_id = self.db.get_store_id_by_address(store)
                
                self.db.update_substitution(user_id, old_date, store_id, old_date, hours)
                await update.message.reply_text("✅ Подмена успешно обновлена!")
            else:
                # Создаем новую подмену
                store_id = context.user_data.get('sub_store_id')
                date = context.user_data.get('sub_date')
                self.db.save_substitution(user_id, store_id, date, hours)
                await update.message.reply_text("✅ Подмена успешно добавлена!")
            
            # Очищаем временные данные
            context.user_data.pop('editing_sub', None)
            context.user_data.pop('old_sub_date', None)
            context.user_data.pop('selected_sub_index', None)
            
            return await self.show_schedule_menu(update, context)
            
        except ValueError:
            await update.message.reply_text("Введите число от 1 до 24")
            return ADD_SUBSTITUTION_HOURS

    async def edit_substitution_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню редактирования подмены"""
        if update.message.text == '↩️ Назад':
            return await self.show_schedule_menu(update, context)

        keyboard = [
            ['✏️ Редактировать подмену'],
            ['❌ Удалить подмену'],
            ['↩️ Назад']
        ]
        await update.message.reply_text(
            'Выберите действие:',
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return EDIT_SUBSTITUTION

    async def handle_substitution_edit_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора действия с подменой"""
        if update.message.text == '↩️ Назад':
            return await self.show_schedule_menu(update, context)

        user_id = context.user_data.get('user_id')
        substitutions = self.db.get_user_substitutions(user_id, datetime.now())

        if not substitutions:
            await update.message.reply_text(
                "У вас нет подмен в текущем месяце.",
                reply_markup=ReplyKeyboardMarkup([['↩️ Назад']], resize_keyboard=True)
            )
            return EDIT_SUBSTITUTION

        # Показываем список подмен с номерами
        substitutions_text = "Ваши подмены:\n\n"
        context.user_data['substitutions'] = substitutions  # Сохраняем список подмен
        for i, (date, hours, store) in enumerate(substitutions, 1):
            substitutions_text += f"{i}. {date}: {hours}ч в {store}\n"

        await update.message.reply_text(
            f"{substitutions_text}\n"
            "Введите номер подмены для редактирования:",
            reply_markup=ReplyKeyboardMarkup([['↩️ Назад']], resize_keyboard=True)
        )
        
        # Сохраняем действие (редактирование или удаление)
        context.user_data['sub_action'] = 'edit' if update.message.text == '✏️ Редактировать подмену' else 'delete'
        return SELECT_SUBSTITUTION_DATE

    async def handle_substitution_date_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора подмены"""
        if update.message.text == '↩️ Назад':
            return await self.edit_substitution_menu(update, context)

        try:
            selected_index = int(update.message.text) - 1
            substitutions = context.user_data.get('substitutions', [])
            
            if not (0 <= selected_index < len(substitutions)):
                await update.message.reply_text(
                    "Неверный номер подмены. Попробуйте еще раз:",
                    reply_markup=ReplyKeyboardMarkup([['↩️ Назад']], resize_keyboard=True)
                )
                return SELECT_SUBSTITUTION_DATE

            date, hours, store = substitutions[selected_index]
            action = context.user_data.get('sub_action')
            user_id = context.user_data.get('user_id')

            if action == 'delete':
                self.db.delete_substitution(user_id, date)
                await update.message.reply_text("✅ Подмена успешно удалена!")
                return await self.show_schedule_menu(update, context)
            else:
                # Сохраняем индекс выбранной подмены
                context.user_data['selected_sub_index'] = selected_index
                context.user_data['old_sub_date'] = date
                context.user_data['editing_sub'] = True
                await update.message.reply_text(
                    f"Текущее количество часов: {hours}\n"
                    "Введите новое количество часов (от 1 до 24):",
                    reply_markup=ReplyKeyboardMarkup([['↩️ Назад']], resize_keyboard=True)
                )
                return ADD_SUBSTITUTION_HOURS

        except ValueError:
            await update.message.reply_text(
                "Пожалуйста, введите номер подмены цифрой",
                reply_markup=ReplyKeyboardMarkup([['↩️ Назад']], resize_keyboard=True)
            )
            return SELECT_SUBSTITUTION_DATE
