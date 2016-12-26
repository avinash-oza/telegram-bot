import os
import argparse
import ConfigParser
import logging
import sys
from telegram.ext import Job, Updater, CommandHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

config = ConfigParser.ConfigParser()
config.read('bot.config')

updater = Updater(token=config.get('KEYS', 'bot_api'))
dispatcher = updater.dispatcher
job_queue = updater.job_queue

env = os.environ
print env
MESSAGE_TEXT="""
***** Nagios *****

Notification Type: {NOTIFICATIONTYPE}
Host: {HOSTNAME}
State: {HOSTSTATE}
Address: {HOSTADDRESS}
Info: {HOSTOUTPUT}

Date/Time: {LONGDATETIME}
""".format(NOTIFICATIONTYPE=env.get('NAGIOS_NOTIFICATIONTYPE'),
            HOSTNAME=env.get('NAGIOS_HOSTNAME'),
            HOSTSTATE=env.get('NAGIOS_HOSTSTATE'),
            HOSTADDRESS=env.get('NAGIOS_HOSTADDRESS'),
            HOSTOUTPUT=env.get('NAGIOS_HOSTOUTPUT'),
            LONGDATETIME=env.get('NAGIOS_LONGDATETIME')
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
