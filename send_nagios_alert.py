import os
import argparse
import ConfigParser
import logging
from telegram.ext import Job, Updater, CommandHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

config = ConfigParser.ConfigParser()
config.read('bot.config')

updater = Updater(token=config.get('KEYS', 'bot_api'))
dispatcher = updater.dispatcher
job_queue = updater.job_queue

env = os.environ
MESSAGE_TEXT="""
***** Nagios *****

Notification Type: {NOTIFICATIONTYPE}
Host: {HOSTNAME}
State: {HOSTSTATE}
Address: {HOSTADDRESS}
Info: {HOSTOUTPUT}

Date/Time: {LONGDATETIME}
""".format(NOTIFICATIONTYPE=env['NOTIFICATIONTYPE'],
            HOSTNAME=env['HOSTNAME'],
            HOSTSTATE=env['HOSTSTATE'],
            HOSTADDRESS=env['HOSTADDRESS'],
            HOSTOUTPUT=env['HOSTOUTPUT'],
            LONGDATETIME=env['LONGDATETIME']
            )

def callback_minute(bot, job):
    bot.sendMessage(chat_id=config.get('ADMIN', 'id'), 
#       text='One message every minute')
        text=MESSAGE_TEXT)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    job_minute = Job(callback_minute, 60.0)
    job_queue.put(job_minute, next_t=0.0)

    updater.start_polling()
    updater.stop()
