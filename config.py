import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Токен бота из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not found in environment variables!")

# Настройки базы данных
DATABASE_NAME = "birthdays.db"

# Интервал проверки дней рождения (в секундах)
CHECK_INTERVAL = 300  # 5 минут

# Время очистки старых напоминаний (в днях)
CLEANUP_DAYS = 3