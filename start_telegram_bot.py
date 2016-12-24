import ConfigParser
import logging
from telegram.ext import Updater

config = ConfigParser.ConfigParser()
config.read('bot.config')

updater = Updater(token=config.get('KEYS', 'bot_api'))
dispatcher = updater.dispatcher

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def start(bot, update):
    logging.info("Got a message")
    bot.sendMessage(chat_id=update.message.chat_id, text="TESTING FROM AVI")

from telegram.ext import CommandHandler
start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

updater.start_polling()
updater.idle()
