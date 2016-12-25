import ConfigParser
import logging
import subprocess
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

def power_status(bot, update, args):
    ip_address = config.get('ADMIN', 'ups_ip') # the ip of the UPS server
    command_to_run = ['/usr/local/nagios/libexec/check_nrpe', '-c', 'show_ups', '-H', ip_address]
    text_output = subprocess.check_output(command_to_run)
    bot.sendMessage(chat_id=update.message.chat_id, text=text_output)

power_status_handler = CommandHandler('powerStatus', power_status, pass_args=True)
dispatcher.add_handler(power_status_handler)

#job_minute = Job(callback_minute, 60.0)
#job_queue.put(job_minute, next_t=0.0)

updater.start_polling()
updater.idle()
