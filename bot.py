import os
import sys

# Добавляем путь для импортов
sys.path.append(os.path.dirname(__file__))

from main import UniversalBot, BOT_TOKEN

if __name__ == '__main__':
    bot = UniversalBot(BOT_TOKEN)
    bot.application.run_polling()