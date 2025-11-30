import sqlite3
from datetime import datetime, timedelta
import os

class Database:
    def __init__(self, db_name='birthdays.db'):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_name, check_same_thread=False)
        cursor = conn.cursor()

        # Создаем таблицу для дней рождения
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS birthdays (
                user_id INTEGER,
                chat_id INTEGER,
                birthday_date TEXT,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                PRIMARY KEY (user_id, chat_id)
            )
        ''')

        # Создаем таблицу для отслеживания отправленных напоминаний
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sent_reminders (
                user_id INTEGER,
                chat_id INTEGER,
                reminder_date TEXT,
                reminder_type TEXT,
                PRIMARY KEY (user_id, chat_id, reminder_date, reminder_type)
            )
        ''')

        conn.commit()
        conn.close()
        print("✅ База данных инициализирована")

    def add_birthday(self, user_id, chat_id, birthday_date, username, first_name, last_name):
        """Добавление дня рождения"""
        conn = sqlite3.connect(self.db_name, check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO birthdays (user_id, chat_id, birthday_date, username, first_name, last_name)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, chat_id, birthday_date, username, first_name, last_name))

        conn.commit()
        conn.close()
        print(f"✅ День рождения сохранен для user_id: {user_id}")

    def get_all_birthdays(self):
        """Получение всех дней рождения"""
        conn = sqlite3.connect(self.db_name, check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute('SELECT user_id, chat_id, birthday_date, username, first_name, last_name FROM birthdays')
        birthdays = cursor.fetchall()

        conn.close()
        return birthdays

    def get_chat_birthdays(self, chat_id):
        """Получение дней рождения для конкретного чата"""
        conn = sqlite3.connect(self.db_name, check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT user_id, chat_id, birthday_date, username, first_name, last_name 
            FROM birthdays 
            WHERE chat_id = ?
        ''', (chat_id,))
        birthdays = cursor.fetchall()

        conn.close()
        return birthdays

    def get_chat_members(self, chat_id):
        """Получение всех участников чата"""
        conn = sqlite3.connect(self.db_name, check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute('SELECT DISTINCT user_id FROM birthdays WHERE chat_id = ?', (chat_id,))
        members = cursor.fetchall()

        conn.close()
        return [member[0] for member in members]

    def get_user_birthday(self, user_id, chat_id):
        """Получение дня рождения конкретного пользователя"""
        conn = sqlite3.connect(self.db_name, check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM birthdays WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
        birthday = cursor.fetchone()

        conn.close()
        return birthday

    def delete_birthday(self, user_id, chat_id):
        """Удаление дня рождения"""
        conn = sqlite3.connect(self.db_name, check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM birthdays WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))

        conn.commit()
        conn.close()
        print(f"✅ День рождения удален для user_id: {user_id}")

    def get_tomorrow_birthdays(self):
        """Получение дней рождения на завтра"""
        conn = sqlite3.connect(self.db_name, check_same_thread=False)
        cursor = conn.cursor()

        tomorrow = (datetime.now() + timedelta(days=1))
        tomorrow_month_day = tomorrow.strftime("%m-%d")

        cursor.execute('''
            SELECT user_id, chat_id, birthday_date, username, first_name, last_name 
            FROM birthdays 
            WHERE substr(birthday_date, 6, 5) = ?
        ''', (tomorrow_month_day,))
        birthdays = cursor.fetchall()

        conn.close()
        print(f"🎯 Найдено дней рождения на завтра: {len(birthdays)}")
        return birthdays

    def get_today_birthdays(self):
        """Получение дней рождения на сегодня"""
        conn = sqlite3.connect(self.db_name, check_same_thread=False)
        cursor = conn.cursor()

        today = datetime.now()
        today_month_day = today.strftime("%m-%d")

        cursor.execute('''
            SELECT user_id, chat_id, birthday_date, username, first_name, last_name 
            FROM birthdays 
            WHERE substr(birthday_date, 6, 5) = ?
        ''', (today_month_day,))
        birthdays = cursor.fetchall()

        conn.close()
        print(f"🎯 Найдено дней рождения на сегодня: {len(birthdays)}")
        return birthdays

    def add_sent_reminder(self, user_id, chat_id, reminder_date, reminder_type):
        """Добавление записи об отправленном напоминании"""
        conn = sqlite3.connect(self.db_name, check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO sent_reminders (user_id, chat_id, reminder_date, reminder_type)
            VALUES (?, ?, ?, ?)
        ''', (user_id, chat_id, reminder_date, reminder_type))

        conn.commit()
        conn.close()
        print(f"✅ Напоминание сохранено для user_id: {user_id}, тип: {reminder_type}")

    def is_reminder_sent(self, user_id, chat_id, reminder_date, reminder_type):
        """Проверка, было ли уже отправлено напоминание"""
        conn = sqlite3.connect(self.db_name, check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT 1 FROM sent_reminders 
            WHERE user_id = ? AND chat_id = ? AND reminder_date = ? AND reminder_type = ?
        ''', (user_id, chat_id, reminder_date, reminder_type))

        result = cursor.fetchone()
        conn.close()

        return result is not None

    def cleanup_old_reminders(self):
        """Очистка старых напоминаний (старше 3 дней)"""
        conn = sqlite3.connect(self.db_name, check_same_thread=False)
        cursor = conn.cursor()

        three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")

        cursor.execute('''
            DELETE FROM sent_reminders 
            WHERE reminder_date < ?
        ''', (three_days_ago,))

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted_count > 0:
            print(f"🧹 Удалено старых напоминаний: {deleted_count}")

    def backup_database(self):
        """Создание резервной копии базы данных"""
        if os.path.exists(self.db_name):
            import shutil
            backup_name = f"{self.db_name}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(self.db_name, backup_name)
            print(f"✅ Создана резервная копия: {backup_name}")

    def get_database_stats(self):
        """Получение статистики базы данных"""
        conn = sqlite3.connect(self.db_name, check_same_thread=False)
        cursor = conn.cursor()

        # Количество записей о днях рождения
        cursor.execute('SELECT COUNT(*) FROM birthdays')
        birthdays_count = cursor.fetchone()[0]

        # Количество уникальных чатов
        cursor.execute('SELECT COUNT(DISTINCT chat_id) FROM birthdays')
        chats_count = cursor.fetchone()[0]

        # Количество уникальных пользователей
        cursor.execute('SELECT COUNT(DISTINCT user_id) FROM birthdays')
        users_count = cursor.fetchone()[0]

        conn.close()

        return {
            'birthdays_count': birthdays_count,
            'chats_count': chats_count,
            'users_count': users_count
        }