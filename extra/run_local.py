from telegram.ext import Updater
from telegram_bot.webhook import setup_handlers
from telegram_bot.config_util import ConfigHelper

if __name__ == '__main__':
    c = ConfigHelper()
    TELEGRAM_TOKEN = c.get('telegram', 'api_key')

    updater = Updater(token=TELEGRAM_TOKEN)
    dispatcher = updater.dispatcher
    setup_handlers(dispatcher)

    updater.start_polling()