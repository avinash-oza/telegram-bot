import ConfigParser
import logging
import subprocess
import time
import sqlite3
import collections
from telegram.ext import Job, Updater, CommandHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

config = ConfigParser.ConfigParser()
config.read('bot.config')

updater = Updater(token=config.get('KEYS', 'bot_api'))
dispatcher = updater.dispatcher
job_queue = updater.job_queue

def send_nagios_alerts(bot, job):
    """
    Retrieves alerts and sends them
    """
    admin_id = config.get('ADMIN', 'id')

    # Open the database
    conn = sqlite3.connect('alerts.db')
    c = conn.cursor()
    # Get the current unsent alerts
    unsent_alerts = c.execute("SELECT id date_inserted,date_sent,message_text,status FROM NAGIOS_ALERTS WHERE STATUS='UNSENT'")

    # Send the alerts which are not sent
    for one_alert in unsent_alerts:
        # First update the alert to be SENT
        alert_id = one_alert[0]
        alert_text = one_alert[2]
        c.execute("UPDATE NAGIOS_ALERTS SET STATUS='SENT' where id=?", (alert_id,) )
        # Send the message after we are sure the update occured
        bot.sendMessage(chat_id=admin_id, text=alert_text)
        # Sleep a bit to make sure we don't spam the api
        print alert_text
        time.sleep(2)

def power_status(bot, update, args):
    ip_address = config.get('ADMIN', 'ups_ip') # the ip of the UPS server
    command_to_run = ['/usr/local/nagios/libexec/check_nrpe', '-c', 'show_ups', '-H', ip_address]
    text_output = subprocess.check_output(command_to_run)
    bot.sendMessage(chat_id=update.message.chat_id, text=text_output)

if __name__ == '__main__':
    power_status_handler = CommandHandler('powerStatus', power_status, pass_args=True)
    dispatcher.add_handler(power_status_handler)

    # Create the job to check if we have any nagios alerts to send
    job_minute = Job(send_nagios_alerts, 60.0)
    job_queue.put(job_minute, next_t=0.0)

    updater.start_polling()
    updater.idle()
