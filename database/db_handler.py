import sqlite3
from typing import Optional, Tuple, List
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta

logger = logging.getLogger('TelegramBot')

class DatabaseHandler:
    def __init__(self, db_name: str):
        self.db_name = db_name
        self.setup_database()

    def setup_database(self):
        """Создание и обновление структуры базы данных"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        # Таблица магазинов
        c.execute('''CREATE TABLE IF NOT EXISTS stores
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      store_number TEXT UNIQUE,
                      address TEXT)''')
        
        # Таблица связи администраторов с магазинами
        c.execute('''CREATE TABLE IF NOT EXISTS admin_stores
                     (admin_id INTEGER,
                      store_id INTEGER,
                      FOREIGN KEY(admin_id) REFERENCES users(id),
                      FOREIGN KEY(store_id) REFERENCES stores(id),
                      PRIMARY KEY(admin_id, store_id))''')
        
        # Обновляем аблицу пользователей
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      telegram_id INTEGER,
                      full_name TEXT,
                      barcode TEXT UNIQUE,
                      hire_date TEXT,
                      is_admin INTEGER DEFAULT 0,
                      position TEXT DEFAULT 'Кассир Торгового Зала',
                      work_store_id INTEGER,
                      FOREIGN KEY(work_store_id) REFERENCES stores(id))''')
        
        # Таблица графиков
        c.execute('''CREATE TABLE IF NOT EXISTS schedules
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      store_id INTEGER,
                      month TEXT,
                      schedule_data TEXT,
                      FOREIGN KEY(user_id) REFERENCES users(id),
                      FOREIGN KEY(store_id) REFERENCES stores(id))''')
        
        conn.commit()
        conn.close()

    def add_user(self, telegram_id: int, full_name: str, barcode: str, work_store_id: Optional[int] = None) -> int:
        """Добавление нового пользователя"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('''INSERT INTO users 
                    (telegram_id, full_name, barcode, position, work_store_id) 
                    VALUES (?, ?, ?, ?, ?)''',
                 (telegram_id, full_name, barcode, "Кассир Торгового Зала", work_store_id))
        user_id = c.lastrowid
        conn.commit()
        conn.close()
        return user_id

    def get_user_by_barcode(self, barcode: str) -> Optional[Tuple]:
        """Получение пользователя по штрих-коду"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('SELECT id FROM users WHERE barcode = ?', (barcode,))
        result = c.fetchone()
        conn.close()
        return result

    def get_user_data(self, user_id: int) -> Optional[Tuple]:
        """Получение данных пользователя"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('''
            SELECT 
                u.full_name,
                u.barcode,
                u.hire_date,
                u.position,
                u.is_admin,
                u.work_store_id,
                s.address
            FROM users u
            LEFT JOIN stores s ON u.work_store_id = s.id
            WHERE u.id = ?
        ''', (user_id,))
        user_data = c.fetchone()
        conn.close()
        return user_data

    def update_user_name(self, user_id: int, new_name: str):
        """Обновление имени пользователя"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('UPDATE users SET full_name = ? WHERE id = ?', 
                 (new_name, user_id))
        conn.commit()
        conn.close()

    def update_user_barcode(self, user_id: int, new_barcode: str):
        """Обновление штрих-кода пользователя"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('UPDATE users SET barcode = ? WHERE id = ?', 
                 (new_barcode, user_id))
        conn.commit()
        conn.close()

    def update_hire_date(self, user_id: int, hire_date: str):
        """Обновление даты трудоустройства"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('UPDATE users SET hire_date = ? WHERE id = ?', 
                 (hire_date, user_id))
        conn.commit()
        conn.close()

    def set_admin_status(self, user_id: int, is_admin: bool):
        """Установка статуса администратора"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('UPDATE users SET is_admin = ? WHERE id = ?', 
                 (1 if is_admin else 0, user_id))
        conn.commit()
        conn.close()

    def is_user_admin(self, user_id: int) -> bool:
        """Проверка статуса админа"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('SELECT is_admin FROM users WHERE id = ?', (user_id,))
        result = c.fetchone()
        conn.close()
        return bool(result[0]) if result else False

    def get_all_users(self):
        """Получение списка всех пользователей"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('SELECT id, full_name, barcode, hire_date, is_admin, position FROM users')
        users = c.fetchall()
        conn.close()
        return users

    def update_user_position(self, user_id: int, position: str):
        """Обновление должности пользователя"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        # Начинаем транзакцию
        c.execute('BEGIN TRANSACTION')
        try:
            # Получаем текущие данные пользователя
            c.execute('SELECT is_admin FROM users WHERE id = ?', (user_id,))
            current_admin_status = c.fetchone()[0]
            
            # Обновляем должность
            c.execute('UPDATE users SET position = ? WHERE id = ?', (position, user_id))
            
            # Если должность КРО, СБ или Тер.менеджер - убираем привязку к магазину
            if position in ['КРО', 'Служба Безопасности', 'Территориальный менеджер']:
                c.execute('UPDATE users SET work_store_id = NULL WHERE id = ?', (user_id,))
                # Убираем прикрепленные магазины в любом случае
                c.execute('DELETE FROM admin_stores WHERE admin_id = ?', (user_id,))
                
                # Автоматически даем права админа для Территориального менеджера
                if position == 'Территориальный менеджер':
                    c.execute('UPDATE users SET is_admin = 1 WHERE id = ?', (user_id,))
            
            # Если лжность Администратор - всегда даем права админа
            elif position == 'Администратор':
                c.execute('UPDATE users SET is_admin = 1 WHERE id = ?', (user_id,))
            
            # Для остальных долностей сохраняем текущий статус админа
            else:
                pass
            
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Ошибка при обнвлении должности: {e}")
        finally:
            conn.close()

    def get_next_store_number(self) -> str:
        """Получение следующего номера магазина"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) + 1 FROM stores')
        next_number = c.fetchone()[0]
        conn.close()
        return f"M{next_number:03d}"  # Format: M001, M002, etc.

    def add_store(self, address: str) -> Optional[int]:
        """Добавление нового магазина"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        try:
            store_number = self.get_next_store_number()
            c.execute('INSERT INTO stores (store_number, address) VALUES (?, ?)',
                     (store_number, address))
            store_id = c.lastrowid
            conn.commit()
            conn.close()
            return store_id
        except sqlite3.Error:
            conn.close()
            return None

    def get_all_stores(self) -> List[Tuple]:
        """Получение списка всех магазинов"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('SELECT id, store_number, address FROM stores')
        stores = c.fetchall()
        conn.close()
        return stores

    def get_store_by_id(self, store_id: int) -> Optional[Tuple]:
        """Получение магазина по ID"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('SELECT id, store_number, address FROM stores WHERE id = ?', (store_id,))
        store = c.fetchone()
        conn.close()
        return store

    def update_user_store(self, user_id: int, store_id: Optional[int]):
        """Обновление магазина пользователя"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('UPDATE users SET work_store_id = ? WHERE id = ?', 
                 (store_id, user_id))
        conn.commit()
        conn.close()

    def assign_stores_to_admin(self, admin_id: int, store_ids: list):
        """Прикрепление магазинов к администратору"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        # Удаляем старые связи
        c.execute('DELETE FROM admin_stores WHERE admin_id = ?', (admin_id,))
        # Дбавляем новые связи
        for store_id in store_ids:
            c.execute('INSERT INTO admin_stores (admin_id, store_id) VALUES (?, ?)',
                     (admin_id, store_id))
        conn.commit()
        conn.close()

    def get_admin_stores(self, admin_id: int):
        """Получение списка магазинов администратора"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('''SELECT s.id, s.store_number, s.address 
                    FROM stores s 
                    JOIN admin_stores as_link ON s.id = as_link.store_id 
                    WHERE as_link.admin_id = ?''', (admin_id,))
        stores = c.fetchall()
        conn.close()
        return stores

    def get_administrators(self) -> List[Tuple]:
        """Получение списка администраторов"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('SELECT id, full_name FROM users WHERE is_admin = 1')
        admins = c.fetchall()
        conn.close()
        return admins

    def get_non_admin_users(self) -> List[Tuple]:
        """Получение списка пльзователей, не являющихся администраторами"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('SELECT id, full_name FROM users WHERE is_admin = 0')
        users = c.fetchall()
        conn.close()
        return users

    def get_store_employees(self, store_id: int) -> List[Tuple]:
        """Получение списка сотрудников магазина"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('''SELECT id, full_name, position 
                    FROM users 
                    WHERE work_store_id = ? 
                    AND position != 'КРО' 
                    AND position != 'Территориальный менеджер' 
                    AND position != 'Служба Безопасности' ''', 
                 (store_id,))
        employees = c.fetchall()
        conn.close()
        return employees

    def check_store_number_exists(self, store_number: str) -> bool:
        """Проверка существования магазина с указанным номером"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('SELECT id FROM stores WHERE store_number = ?', (store_number,))
        result = c.fetchone() is not None
        conn.close()
        return result

    def get_user_id_by_barcode(self, barcode: str) -> Optional[int]:
        """Получение ID пользователя по штрих-коду"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('SELECT id FROM users WHERE barcode = ?', (barcode,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

    def remove_all_admin_stores(self, user_id):
        """Удаляет все прикрепленные магазины у администратора"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('DELETE FROM admin_stores WHERE admin_id = ?', (user_id,))
        conn.commit()
        conn.close()

    def get_store_employees_count(self, store_id: int) -> int:
        """Получение количества сотрудников магазина"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('''SELECT COUNT(*) FROM users 
                    WHERE work_store_id = ? 
                    AND position != 'КРО' 
                    AND position != 'Территориальный менеджер' 
                    AND position != 'Служба Безопасности' ''', 
                 (store_id,))
        count = c.fetchone()[0]
        conn.close()
        return count

    def save_schedule(self, user_id: int, store_id: int, month: str, schedule_data: str):
        """Сохранение графика работы"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO schedules 
                     (user_id, store_id, month, schedule_data) 
                     VALUES (?, ?, ?, ?)''',
                  (user_id, store_id, month, schedule_data))
        conn.commit()
        conn.close()

    def get_schedule(self, user_id: int, store_id: int, month: str) -> Optional[str]:
        """Получение графика работы пользователя"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        c.execute('''SELECT schedule_data 
                     FROM schedules 
                     WHERE user_id = ? AND store_id = ? AND month = ?''',
                  (user_id, store_id, month))
        
        result = c.fetchone()
        conn.close()
        
        return result[0] if result else None

    def get_store_schedules(self, store_id: int, month: str) -> List[Tuple]:
        """Получение всех графиков магазина за месяц"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('''SELECT u.full_name, s.schedule_data 
                     FROM schedules s
                     JOIN users u ON s.user_id = u.id
                     WHERE s.store_id = ? AND s.month = ?''',
                  (store_id, month))
        results = c.fetchall()
        conn.close()
        return results

    def get_user_substitutions(self, user_id: int, month: datetime) -> List[Tuple]:
        """Получение подмен пользователя за месяц"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        # Создаем таблицу подмен, если она не существует
        c.execute('''CREATE TABLE IF NOT EXISTS substitutions
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      store_id INTEGER,
                      date TEXT,
                      hours INTEGER,
                      FOREIGN KEY(user_id) REFERENCES users(id),
                      FOREIGN KEY(store_id) REFERENCES stores(id))''')
        
        # Получаем все подмены пользователя за указанный месяц
        month_start = month.replace(day=1).strftime('%Y-%m-%d')
        month_end = (month.replace(day=1) + relativedelta(months=1, days=-1)).strftime('%Y-%m-%d')
        
        c.execute('''SELECT s.date, s.hours, st.address 
                     FROM substitutions s
                     JOIN stores st ON s.store_id = st.id
                     WHERE s.user_id = ? AND s.date BETWEEN ? AND ?
                     ORDER BY s.date''',
                  (user_id, month_start, month_end))
        
        substitutions = c.fetchall()
        conn.close()
        return substitutions

    def save_substitution(self, user_id: int, store_id: int, date: str, hours: int):
        """Сохранение подмены"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        # Создаем таблицу подмен, если она не существует
        c.execute('''CREATE TABLE IF NOT EXISTS substitutions
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      store_id INTEGER,
                      date TEXT,
                      hours INTEGER,
                      FOREIGN KEY(user_id) REFERENCES users(id),
                      FOREIGN KEY(store_id) REFERENCES stores(id))''')
        
        # Сохраняем данные о подмене
        c.execute('''INSERT INTO substitutions 
                     (user_id, store_id, date, hours)
                     VALUES (?, ?, ?, ?)''',
                  (user_id, store_id, date, hours))
        
        conn.commit()
        conn.close()

    def delete_substitution(self, user_id: int, date: str):
        """Удаление подмены"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('DELETE FROM substitutions WHERE user_id = ? AND date = ?',
                  (user_id, date))
        conn.commit()
        conn.close()

    def update_substitution(self, user_id: int, old_date: str, new_store_id: int, new_date: str, new_hours: int):
        """Обновление подмены"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('''UPDATE substitutions 
                     SET store_id = ?, date = ?, hours = ?
                     WHERE user_id = ? AND date = ?''',
                  (new_store_id, new_date, new_hours, user_id, old_date))
        conn.commit()
        conn.close()

    def get_store_id_by_address(self, address: str) -> Optional[int]:
        """Получение ID магазина по адресу"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('SELECT id FROM stores WHERE address = ?', (address,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None