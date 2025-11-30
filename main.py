import logging
from datetime import datetime, timedelta
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from dateutil.parser import parse
import sqlite3
import asyncio
import threading
import time
import os

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN', '8581961551:AAGFlhCEzZc3k6veVoU3QTOJ41YVyTGEw6o')

print("🚀 Запуск объединенного бота...")

# Состояния для ConversationHandler
SET_BIRTHDAY = 1

# Данные для тегов
groups_data = {
    "команда": [
        {"username": "welIweIIweIl"},
        {"username": "Viper_DQ"},
        {"username": "winterwort"},
        {"username": "zhukov_nes"},
        {"username": "SHAHmirozdanie"}
    ],
    "тренер": [
        {"username": "Dedusmlbb"},
        {"username": "Margul95"}
    ],
    "начальник": [
        {"username": "rickreygan"},
        {"username": "qqueasiness"}
    ],
    "аналитик": [
        {"username": "KeepOnDaaancing"},
    ],
    "менеджер": [
        {"username": "PredatoryIrbis"},
    ],
    "психолог": [
        {"username": "Rygen_ml"},
    ],
    "смм": [
        {"username": "KystVDele"},
        {"username": "HanjiS_live"},
    ],
    "хуёжник": [
        {"username": "TaiBurs"},
    ]
}


class Database:
    def __init__(self, db_name='birthdays.db'):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_name, check_same_thread=False)
        cursor = conn.cursor()

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
        """Очистка старых напоминаний"""
        conn = sqlite3.connect(self.db_name, check_same_thread=False)
        cursor = conn.cursor()

        three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")

        cursor.execute('''
            DELETE FROM sent_reminders 
            WHERE reminder_date < ?
        ''', (three_days_ago,))

        conn.commit()
        conn.close()


# Инициализация базы данных
db = Database()


class UniversalBot:
    def __init__(self, token):
        self.token = token
        self.application = Application.builder().token(token).build()
        self.setup_handlers()

    def setup_handlers(self):
        """Настройка обработчиков команд"""
        # Обработчик для установки дня рождения с состоянием
        set_birthday_handler = ConversationHandler(
            entry_points=[CommandHandler("set_birthday", self.set_birthday_command)],
            states={
                SET_BIRTHDAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_birthday_date)]
            },
            fallbacks=[CommandHandler("cancel", self.cancel_birthday_input)]
        )

        # Команды дней рождения
        self.application.add_handler(set_birthday_handler)
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("my_birthday", self.my_birthday_command))
        self.application.add_handler(CommandHandler("birthdays", self.birthdays_command))

        # Команды тегов
        self.application.add_handler(CommandHandler("groups", self.groups_command))
        self.application.add_handler(CommandHandler("tags", self.tags_command))

        # Общие команды
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("cancel", self.cancel_command))

        # Обработчик сообщений для тегов
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_message
        ))

    async def setup_commands(self, application):
        """Настройка подсказок команд"""
        commands = [
            ("start", "Начать работу с ботом"),
            ("set_birthday", "Установить день рождения"),
            ("my_birthday", "Посмотреть свою дату рождения"),
            ("birthdays", "Список дней рождения в группе"),
            ("groups", "Показать состав групп для тегов"),
            ("tags", "Список доступных тегов"),
            ("help", "Показать справку по командам"),
            ("cancel", "Отменить текущее действие")
        ]
        await application.bot.set_my_commands(commands)
        logger.info("✅ Bot commands setup completed")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        chat_type = update.effective_chat.type

        if chat_type == "private":
            await update.message.reply_text(
                "🎉🤖 <b>Универсальный бот - Дни рождения и Теги!</b>\n\n"
                "Я совмещаю две функции:\n\n"
                "🎂 <b>Дни рождения:</b>\n"
                "• Напоминания о ДР участников\n"
                "• Поздравления в группе\n"
                "• Список всех дней рождения\n\n"
                "🏷️ <b>Теги:</b>\n"
                "• Быстрое упоминание групп\n"
                "• @команда, @тренер, @начальник и др.\n\n"
                "📌 <b>Добавьте меня в группу</b> для полного функционала!\n\n"
                "📋 Команды: /help",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "🎉🤖 <b>Универсальный бот активирован!</b>\n\n"
                "Теперь я буду:\n\n"
                "🎂 <b>Следить за днями рождения:</b>\n"
                "• Напоминать за день до ДР\n"
                "• Поздравлять именинников\n"
                "• Хранить список ДР\n\n"
                "🏷️ <b>Упоминать группы:</b>\n"
                "• @команда - упомянуть команду\n"
                "• @тренер - упомянуть тренеров\n"
                "• И другие теги\n\n"
                "📋 <b>Основные команды:</b>\n"
                "/set_birthday - установить ДР\n"
                "/birthdays - список ДР\n"
                "/groups - состав групп\n"
                "/tags - доступные теги\n"
                "/help - помощь",
                parse_mode='HTML'
            )

    # === КОМАНДЫ ДНЕЙ РОЖДЕНИЯ ===

    async def set_birthday_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Установка дня рождения"""
        chat_type = update.effective_chat.type

        if chat_type == "private":
            await update.message.reply_text("❌ Эту команду нужно использовать в группе!")
            return ConversationHandler.END

        await update.message.reply_text(
            "📅 <b>Установка дня рождения</b>\n\n"
            "Введите дату в формате: <code>ДД.ММ.ГГГГ</code>\n\n"
            "📝 <b>Примеры:</b>\n"
            "• 15.05.1990\n"
            "• 03.12.1985\n"
            "• 25.01.2000\n"
            "• 29.11.00\n"
            "• 15.05 (текущий год)\n\n"
            "❌ <b>Отмена:</b> /cancel",
            parse_mode='HTML'
        )
        return SET_BIRTHDAY

    async def process_birthday_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка введенной даты рождения"""
        date_str = update.message.text.strip()

        try:
            date_str = date_str.replace('/', '.').replace('-', '.')

            formats_to_try = ['%d.%m.%Y', '%d.%m.%y', '%d.%m']
            parsed_date = None

            for fmt in formats_to_try:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue

            if parsed_date is None:
                try:
                    parsed_date = parse(date_str, dayfirst=True)
                except:
                    raise ValueError("Не удалось распознать дату")

            # Если введена дата без года, используем текущий год
            if len(date_str.split('.')) == 2:
                birthday_date = parsed_date.replace(year=datetime.now().year).date()
            else:
                birthday_date = parsed_date.date()

            if birthday_date > datetime.now().date():
                await update.message.reply_text("❌ Дата рождения не может быть в будущем!")
                return SET_BIRTHDAY

            user = update.effective_user
            chat = update.effective_chat
            birthday_str = birthday_date.strftime("%Y-%m-%d")

            db.add_birthday(
                user_id=user.id,
                chat_id=chat.id,
                birthday_date=birthday_str,
                username=user.username or "",
                first_name=user.first_name or "",
                last_name=user.last_name or ""
            )

            await update.message.reply_text(
                f"✅ <b>Отлично, {user.first_name}!</b>\n\n"
                f"🎂 Ваш день рождения установлен на <b>{birthday_date.strftime('%d.%m.%Y')}</b>\n\n"
                f"📢 Теперь участники будут получать напоминания о вашем ДР!",
                parse_mode='HTML'
            )

            return ConversationHandler.END

        except ValueError:
            await update.message.reply_text(
                "❌ <b>Неверный формат даты!</b>\n\n"
                "Пожалуйста, введите дату в формате: <code>ДД.ММ.ГГГГ</code>\n\n"
                "✅ <b>Примеры:</b>\n"
                "• 15.05.1990\n"
                "• 03.12.1985\n"
                "• 25.01.2000\n\n"
                "❌ <b>Отмена:</b> /cancel",
                parse_mode='HTML'
            )
            return SET_BIRTHDAY
        except Exception as e:
            logger.error(f"Error setting birthday: {e}")
            await update.message.reply_text("❌ Произошла ошибка при сохранении даты.")
            return ConversationHandler.END

    async def cancel_birthday_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена ввода дня рождения"""
        await update.message.reply_text("❌ Ввод дня рождения отменен.")
        return ConversationHandler.END

    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /cancel"""
        await update.message.reply_text("ℹ️ Нет активных действий для отмены.")

    async def my_birthday_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать установленный день рождения"""
        user = update.effective_user
        chat = update.effective_chat

        birthday = db.get_user_birthday(user.id, chat.id)

        if birthday:
            birthday_date = datetime.strptime(birthday[2], "%Y-%m-%d").strftime("%d.%m.%Y")
            await update.message.reply_text(
                f"🎂 <b>Ваш день рождения:</b>\n"
                f"📅 {birthday_date}\n\n"
                f"✏️ Изменить: /set_birthday",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "❌ <b>У вас не установлен день рождения</b>\n\n"
                "📅 Установите его:\n"
                "/set_birthday",
                parse_mode='HTML'
            )

    async def birthdays_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать все дни рождения в группе"""
        chat = update.effective_chat

        if chat.type == "private":
            await update.message.reply_text("❌ Эту команду нужно использовать в группе!")
            return

        birthdays = db.get_chat_birthdays(chat.id)

        if not birthdays:
            await update.message.reply_text(
                "📅 <b>В этой группе пока нет установленных дней рождения</b>\n\n"
                "Станьте первым!\n"
                "/set_birthday",
                parse_mode='HTML'
            )
            return

        birthdays_sorted = sorted(birthdays, key=lambda x: x[2][5:])
        message = "🎉 <b>Дни рождения участников:</b>\n\n"

        for i, bday in enumerate(birthdays_sorted, 1):
            user_id, chat_id, birthday_date, username, first_name, last_name = bday
            display_name = first_name
            if last_name:
                display_name += f" {last_name}"
            elif username:
                display_name += f" (@{username})"

            date_obj = datetime.strptime(birthday_date, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%d.%m.%Y")

            message += f"{i}. {display_name} - {formatted_date}\n"

        message += f"\n📊 Всего: {len(birthdays)} человек(а)"
        await update.message.reply_text(message, parse_mode='HTML')

    # === КОМАНДЫ ТЕГОВ ===

    async def groups_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать состав групп"""
        groups_text = "👥 <b>Состав групп:</b>\n\n"
        for group_name, members in groups_data.items():
            groups_text += f"<b>{group_name.upper()}:</b>\n"
            for i, member in enumerate(members, 1):
                groups_text += f"{i}. @{member['username']}\n"
            groups_text += "\n"
        await update.message.reply_text(groups_text, parse_mode='HTML')

    async def tags_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать доступные теги"""
        tags_text = "🏷️ <b>Доступные теги:</b>\n\n"
        tags_text += "Просто напишите в чате:\n"
        for group_name in groups_data.keys():
            tags_text += f"• @{group_name}\n"
        tags_text += "\n🤖 Я автоматически упомяну всех участников группы!"
        await update.message.reply_text(tags_text, parse_mode='HTML')

    def create_group_mention(self, group_name: str) -> str:
        """Создание упоминания группы"""
        if group_name not in groups_data:
            return ""
        members = groups_data[group_name]
        mentions = [f"@{member['username']}" for member in members if member['username']]
        return " ".join(mentions)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка сообщений с мгновенными тегами"""
        # МГНОВЕННАЯ обработка тегов
        if update.message and update.message.text:
            message_text = update.message.text

            for group_name in groups_data.keys():
                trigger_word = f"@{group_name}"
                if trigger_word in message_text.lower():
                    mention_text = self.create_group_mention(group_name)
                    if mention_text:
                        # Отвечаем моментально в том же чате
                        try:
                            await update.message.reply_text(
                                mention_text,
                                reply_to_message_id=update.message.message_id
                            )
                        except Exception as e:
                            logger.error(f"Error sending mention: {e}")
                    break

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Справка по командам"""
        await update.message.reply_text(
            "📋 <b>Универсальный бот - Справка</b>\n\n"
            "🎂 <b>Дни рождения:</b>\n"
            "/set_birthday - Установить день рождения\n"
            "/my_birthday - Посмотреть свою дату\n"
            "/birthdays - Список всех ДР в группе\n\n"
            "🏷️ <b>Теги:</b>\n"
            "/groups - Показать состав групп\n"
            "/tags - Список доступных тегов\n\n"
            "💡 <b>Автоматические теги:</b>\n"
            "Просто напишите: @команда, @тренер, @начальник и т.д.\n\n"
            "⏰ <b>Автоматика:</b>\n"
            "• Напоминания о ДР за 1 день\n"
            "• Поздравления в день рождения\n"
            "• Проверка каждые 5 минут\n\n"
            "❌ <b>Отмена действий:</b> /cancel",
            parse_mode='HTML'
        )

    # === СИСТЕМА НАПОМИНАНИЙ ===

    async def check_birthdays(self):
        """Проверка дней рождения и отправка уведомлений"""
        try:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            tomorrow_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")

            # Напоминания на завтра
            tomorrow_birthdays = db.get_tomorrow_birthdays()
            for birthday in tomorrow_birthdays:
                user_id, chat_id, birthday_date, username, first_name, last_name = birthday

                if not db.is_reminder_sent(user_id, chat_id, today_str, "reminder"):
                    chat_members = db.get_chat_members(chat_id)

                    bday_date = datetime.strptime(birthday_date, "%Y-%m-%d")
                    formatted_date = bday_date.strftime("%d.%m.%Y")
                    display_name = first_name
                    if last_name:
                        display_name += f" {last_name}"

                    reminder_sent = False
                    for member_id in chat_members:
                        if member_id != user_id:
                            try:
                                await self.send_reminder_to_user(
                                    member_id, display_name, formatted_date, chat_id
                                )
                                reminder_sent = True
                                await asyncio.sleep(0.1)
                            except Exception as e:
                                logger.error(f"Failed to send reminder: {e}")

                    if reminder_sent:
                        db.add_sent_reminder(user_id, chat_id, today_str, "reminder")

            # Поздравления на сегодня
            today_birthdays = db.get_today_birthdays()
            for birthday in today_birthdays:
                user_id, chat_id, birthday_date, username, first_name, last_name = birthday

                if not db.is_reminder_sent(user_id, chat_id, today_str, "congrats"):
                    birth_year = datetime.strptime(birthday_date, "%Y-%m-%d").year
                    current_year = datetime.now().year
                    age = current_year - birth_year

                    display_name = first_name
                    if last_name:
                        display_name += f" {last_name}"

                    try:
                        await self.send_birthday_congrats(chat_id, display_name, age)
                        db.add_sent_reminder(user_id, chat_id, today_str, "congrats")
                    except Exception as e:
                        logger.error(f"Failed to send congrats: {e}")

            # Очистка старых напоминаний
            if now.hour == 0 and now.minute < 5:
                db.cleanup_old_reminders()

        except Exception as e:
            logger.error(f"Error in check_birthdays: {e}")

    async def send_reminder_to_user(self, user_id, birthday_person, birthday_date, chat_id):
        """Отправка напоминания в ЛС"""
        try:
            message = (
                f"🎉 <b>Напоминание о дне рождения!</b> 🎉\n\n"
                f"Завтра, {birthday_date}, празднует день рождения:\n"
                f"🎂 <b>{birthday_person}</b>\n\n"
                f"Не забудьте поздравить в группе! 🎊"
            )
            await self.application.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Failed to send reminder to user {user_id}: {e}")

    async def send_birthday_congrats(self, chat_id, birthday_person, age):
        """Отправка поздравления в группу"""
        try:
            age_text = f"{age}-летием" if age > 1 else f"{age}-летием"
            message = (
                f"🎂🎉 <b>С ДНЕМ РОЖДЕНИЯ!</b> 🎉🎂\n\n"
                f"Поздравляем <b>{birthday_person}</b> с {age_text}! 🎊\n\n"
                f"💫 Желаем счастья, здоровья, успехов\n"
                f"✨ И всего самого наилучшего! 🎁\n\n"
                f"Присоединяйтесь к поздравлениям! 🎈"
            )
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Failed to send congrats in group {chat_id}: {e}")
            raise

    def start_scheduler(self):
        """Запуск планировщика"""

        def scheduler_loop():
            time.sleep(10)

            while True:
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.check_birthdays())
                    loop.close()
                    time.sleep(300)  # 5 минут
                except Exception as e:
                    logger.error(f"Scheduler error: {e}")
                    time.sleep(300)

        scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
        scheduler_thread.start()
        logger.info("✅ Scheduler started")

    async def post_init(self, application):
        """Выполняется после инициализации бота"""
        await self.setup_commands(application)
        logger.info("🚀 Universal Bot is ready and running!")

    def run(self):
        """Запуск бота"""
        self.application.post_init = self.post_init
        self.start_scheduler()
        logger.info("✅ Starting Universal Bot...")
        self.application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )


def main():
    """Основная функция запуска"""
    bot = UniversalBot(BOT_TOKEN)
    bot.run()


if __name__ == '__main__':
    main()



