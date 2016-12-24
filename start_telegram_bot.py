import ConfigParser
import logging
from telegram.ext import Job, Updater, CommandHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

config = ConfigParser.ConfigParser()
config.read('bot.config')

updater = Updater(token=config.get('KEYS', 'bot_api'))
dispatcher = updater.dispatcher
job_queue = updater.job_queue

def callback_minute(bot, job):
    bot.sendMessage(chat_id=config.get('ADMIN', 'id'), 
        text='One message every minute')

def start(bot, update):
    logging.info("Got a message")
    bot.sendMessage(chat_id=update.message.chat_id, text="TESTING FROM AVI")

start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

job_minute = Job(callback_minute, 60.0)
job_queue.put(job_minute, next_t=0.0)

updater.start_polling()
updater.idle()
