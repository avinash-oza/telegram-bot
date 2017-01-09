import ConfigParser
import logging
import subprocess
import time
import sqlite3
import mysql.connector
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
    db_host_name = config.get('DATABASE', 'host')
    db_user_name = config.get('DATABASE', 'user')
    db_password = config.get('DATABASE', 'password')
    database_name = config.get('DATABASE', 'database')

    conn =  mysql.connector.connect(user=db_user_name,password=db_password,host=db_host_name, database=database_name)
    cursor = conn.cursor(buffered=True)
    c = conn.cursor(buffered=True)
    write_cursor = conn.cursor(buffered=True)
    # Get the current unsent alerts. Make sure to send them in order
    c.execute("SELECT id date_inserted,date_sent,message_text,status FROM nagios_alerts WHERE STATUS='UNSENT' ORDER BY id ASC")
    # Enumerate the counter so we know how many results returned
    results = [one_result for one_result in c]
    total_count_of_alerts = len(results)
    message_str = """"""

    # Send the alerts which are not sent
    for index, one_alert in enumerate(results):
        # First update the alert to be SENT
        alert_id = one_alert[0]
        alert_text = one_alert[2]
        write_cursor.execute("UPDATE nagios_alerts SET status='SENT', date_sent = NOW() where id= {0}".format(alert_id))
        # Send the message after we are sure the update occured
        # Sleep a bit to make sure we don't spam the api
        message_str += alert_text
        if index >= 4:
            # Send 5 messages together at a time and then wait till the next call
            break
        message_str += "--------------------\n"
        print alert_text

    if message_str:
        message_str += "{0}/{1} messages sent".format(index+1, total_count_of_alerts) # Since we start at 0
        bot.sendMessage(chat_id=admin_id, text=message_str)
    # Commit changes and close db
    conn.commit()
    conn.close()

def power_status(bot, update, args):
    ip_address = config.get('ADMIN', 'ups_ip') # the ip of the UPS server
    command_to_run = ['/usr/lib/nagios/plugins/show_ups']
    text_output = subprocess.check_output(command_to_run)
    bot.sendMessage(chat_id=update.message.chat_id, text=text_output)

if __name__ == '__main__':
    power_status_handler = CommandHandler('powerstatus', power_status, pass_args=True)
    dispatcher.add_handler(power_status_handler)

    # Create the job to check if we have any nagios alerts to send
    job_minute = Job(send_nagios_alerts, 60.0)
    job_queue.put(job_minute, next_t=0.0)

    updater.start_polling()
    updater.idle()
