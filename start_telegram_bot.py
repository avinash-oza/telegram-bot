import ConfigParser
import logging
import random
import traceback
import sys
import subprocess
import time
import datetime
import sqlite3
import mysql.connector
import collections
from telegram.ext import Job, Updater, CommandHandler
from telegram.replykeyboardmarkup import ReplyKeyboardMarkup
from telegram.keyboardbutton import KeyboardButton

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TelegramBot(object):

    def __init__(self):
        self.config = ConfigParser.ConfigParser()
        self.config.read('bot.config')
        self.updater = Updater(token=self.config.get('KEYS', 'bot_api'))
        self.dispatcher = self.updater.dispatcher
        self.job_queue = self.updater.job_queue
        self.key_to_alert_id_mapping = [] # Stores the list of keys that have been sent out at the latest alert
        self.garage_codes = {} # Dictionary to hold one time codes to make sure links are not reused
        self.garage_code_expire_job = None # job to handle expiring the codes if a garage is not selected

    def sender_is_admin(self, sender_id):
        sender_id = int(sender_id)
        admin_id = int(self.config.get('ADMIN', 'id'))
        logger.info("Admin id {0}, sender id {1}".format(admin_id, sender_id))
        if sender_id == admin_id:
            return True
        return False

    def send_nagios_alerts(self, bot, job):
        """
        Retrieves alerts and sends them
        """
        # Before starting, clear out any alerts we were waiting for acknoledgement on
        self.key_to_alert_id_mapping[:] = []
        admin_id = self.config.get('ADMIN', 'id')
        logger.info("Getting alerts from db")

        # Open the database
        db_host_name = self.config.get('DATABASE', 'host')
        db_user_name = self.config.get('DATABASE', 'user')
        db_password = self.config.get('DATABASE', 'password')
        database_name = self.config.get('DATABASE', 'database')

        conn =  mysql.connector.connect(user=db_user_name,password=db_password,host=db_host_name, database=database_name)
        cursor = conn.cursor(buffered=True)
        c = conn.cursor(buffered=True)
        write_cursor = conn.cursor(buffered=True)
        # Get the current unsent alerts. Make sure to send them in order
        c.execute("SELECT id date_inserted,date_sent,message_text,status,hostname,service_name, notification_type FROM nagios_alerts WHERE STATUS='UNSENT' ORDER BY id ASC")
        # Enumerate the counter so we know how many results returned
        results = [one_result for one_result in c]
        total_count_of_alerts = len(results)
        logger.info("Got {0} results".format(total_count_of_alerts))
        message_str = """"""

        # Send the alerts which are not sent
        for index, one_alert in enumerate(results):
            # First update the alert to be SENT
            alert_id = one_alert[0]
            alert_text = one_alert[2]
            host_name = one_alert[4]
            service_name = one_alert[5]
            notification_type = one_alert[6]
            write_cursor.execute("UPDATE nagios_alerts SET status='SENT', date_sent = NOW() where id= {0}".format(alert_id))
            logger.info("Update alert id {0} in the db for alerts".format(alert_id))
            # Send the message after we are sure the update occured
            message_str += alert_text
            # Add the alert to lists of alerts we can acknowledge along with a short string
            if notification_type == 'PROBLEM':
                self.key_to_alert_id_mapping.append((alert_id,"{0};{1}".format(host_name, service_name)))
            if index >= 4:
                # Send 5 messages together at a time and then wait till the next call
                break
            message_str += "--------------------\n"
            print alert_text

        if message_str:
            message_str += "{0}/{1} messages sent".format(index+1, total_count_of_alerts) # Since we start at 0
            bot.sendMessage(chat_id=admin_id, text=message_str)
            # Send message with options to acknowledge alerts
            if self.key_to_alert_id_mapping: # We have some alerts that can be acknowledged
                acknowledge_string = """ALERTS THAT CAN BE ACKNOWLEDGED: \n"""
                options = [] # Stores the keys for the keyboard reply
                for index, one_alert in enumerate(self.key_to_alert_id_mapping):
                    key_string = ' '.join(['/acknowledge',str(index)])
                    options.append([ key_string ]) # Store the key for the keyboard
                    acknowledge_string += "{0} : {1} \n".format(index, one_alert[1])

                # Send the message with the keyboard
                reply_keyboard = ReplyKeyboardMarkup(options, one_time_keyboard=True)
                bot.sendMessage(chat_id=admin_id, text=acknowledge_string, reply_markup=reply_keyboard)



        logger.info("Finished sending alerts")
        # Commit changes and close db
        conn.commit()
        conn.close()

    def power_status(self, bot, update, args):
        arguments_to_use = ['status', 'timeleft']
        complete_output = ""

        logger.info("Got request to check power status")
        for one_arg in arguments_to_use:
            command_to_run = ['/usr/lib/nagios/plugins/check_apcupsd {0}'.format(one_arg)]
            complete_output += subprocess.check_output(command_to_run, shell=True)

        bot.sendMessage(chat_id=update.message.chat_id, text=complete_output)
        logger.info("Sent message for power status")

    

    def acknowledge_alert(self, bot, update, args):
        """Takes the given alert and sends a request to acknowledge it.
        For now we just schedule 1 day of downtime so that it is not forgotten
        """
        logger.info("Got request to acknolwedge id {0}".format(args))
        if not args:
            # did not pass us an alert id
            bot.sendMessage(chat_id=update.message.chat_id, text="No alert specified")
            return

        try:
            alert_id, _ = self.key_to_alert_id_mapping[int(args[0])]
        except IndexError:
            # Some how the key they sent does not exist
             logger.info("Did not find alert id {0}".format(args[0]))
             bot.sendMessage(chat_id=update.message.chat_id, text="Key does not exist")
             return
        # Find the alert id if it exists
        # Open the database
        db_host_name = self.config.get('DATABASE', 'host')
        db_user_name = self.config.get('DATABASE', 'user')
        db_password = self.config.get('DATABASE', 'password')
        database_name = self.config.get('DATABASE', 'database')

        conn =  mysql.connector.connect(user=db_user_name,password=db_password,host=db_host_name, database=database_name)
        cursor = conn.cursor(buffered=True)
        query = """SELECT hostname, service_name FROM nagios_alerts where id=%s"""
        cursor.execute(query, (alert_id,))

        # For now we use the downtime command to make sure the alert is not forgotten about
        current_time = int(time.time()) # Time in linux seconds since it doesnt make much of a difference for 1 second
        one_day = 60 * 60 * 24 # represents 24 hours
        end_time = current_time + one_day # represents 24 hours

        #TODO: This needs to be cleaned and commented more
        result = cursor.fetchone()
        command_string = """[{0}] """.format(current_time)
        host_name = result[0]
        service_name = result[1]
        ACK_COMMAND = 'SCHEDULE_SVC_DOWNTIME'
        COMMENT_COMMAND = 'ADD_SVC_COMMENT'
        comment = 'DOWNTIME SCHEDULED VIA TELEGRAM'
        host_and_service_name = ';'.join([host_name, service_name])
        command_string += ';'.join([ACK_COMMAND, host_and_service_name, str(current_time), str(end_time), '1', '0', str(one_day), 'nagiosadmin', comment])
        comment_string = """[{0}] {1};{2}""".format(current_time, COMMENT_COMMAND, ';'.join([host_and_service_name, '1', 'nagiosadmin', comment]))
        command_to_run = """echo '{0}' > /var/lib/nagios3/rw/nagios.cmd"""
        text_output = subprocess.check_output(command_to_run.format(command_string), shell=True)
        text_output = subprocess.check_output(command_to_run.format(comment_string), shell=True)
        bot.sendMessage(chat_id=update.message.chat_id, text="Marked {0} for 1 day of downtime".format(host_and_service_name))

    def _get_garage_position(self, garage_name):
        # Returns whether the garage is open or closed
        # TODO: MOVE TO OWN SCRIPT AND HANDLE MULTIPLE GARAGES

        command_to_run = ["ssh garage-door@pi2 '~/home-projects/pi-zero/check_garage_status {0}'".format(garage_name)]

        try:
            return subprocess.check_output(command_to_run, shell=True)
        except subprocess.CalledProcessError as e:
            #TODO: Expected error is an error code that is raised when garage is opened for nagios
            return e.output
        else:
            return "No output recieved"

    # Action for operating the garage
    def garage(self, bot, update, args):
        return_message = """Pick a garage (facing from the outside)"""
        sender_id = update.message.chat_id
        # Gives menu to select which garage to open
        if not self.sender_is_admin(sender_id):
            bot.sendMessage(chat_id=sender_id, text='Not authorized')
            return

        garages = ['LEFT', 'RIGHT']
        options = [] # Stores the keys for the keyboard reply

        bot.sendMessage(chat_id=sender_id, text="Getting garage status")

        for one_garage in garages:
            # create a one time "code" to store for the garage
            random_code = random.randrange(1000, 10000000)
            self.garage_codes[random_code] = one_garage # Make the code map to garage so we can verify

            # Get current status for garage
            current_position = self._get_garage_position(one_garage)
            return_message += ' '.join(['\n', one_garage, current_position])

            # Calculate whether to write OPEN or CLOSE
            if 'OPEN' in current_position:
                action = 'CLOSE'
            else:
                action = 'OPEN'

            key_string = ' '.join(['/confirm {0}'.format(random_code), action,  str(one_garage)])
            options.append([ key_string ]) # Store the key for the keyboard

        # Send the message with the keyboard
        reply_keyboard = ReplyKeyboardMarkup(options, one_time_keyboard=True)
        bot.sendMessage(chat_id=sender_id, text=return_message, reply_markup=reply_keyboard)

        # Add handler to expire the codes if we dont hear back in 10 seconds
        def expire_codes(bot, job):
            # Clear the dict as time expired
            self.garage_codes = {}
            bot.sendMessage(chat_id=sender_id, text='Timeout reached. Please start again')

        # Add job to expire codes
        self.garage_code_expire_job = Job(expire_codes, 15.0, repeat=False)
        self.job_queue.put(self.garage_code_expire_job)

    def _open_garage(self, garage_name):
        # Actually invokes the code to open the garage
        command_to_run = ["ssh garage-door@pi2 'python ~/home-projects/pi-zero/relay_trigger.py {0}'".format(garage_name)]
        logger.info("START invoke code to trigger {0} garage".format(garage_name))
        _ =  subprocess.check_output(command_to_run, shell=True)
        logger.info("FINISH invoke code to trigger {0} garage".format(garage_name))

    def confirm_garage_action(self, bot, update, args):
        garage_code, action, _ = args
        sender_id = update.message.chat_id

        # See if there is a pending job to expire the codes. Stop running it if there is
        if self.garage_code_expire_job is not None:
            self.garage_code_expire_job.schedule_removal()
            self.garage_code_expire_job = None

        if not self.sender_is_admin(update.message.chat_id):
            bot.sendMessage(chat_id=sender_id, text='Not authorized')
            return
        # Open the garage if the code matches. Use the code to find which garage
        garage_name = self.garage_codes.get(int(garage_code))
        logger.info("Garage codes were: {0} and garage code passed was {1}".format(self.garage_codes, garage_code))
        if garage_name:
            # Valid code was passed. Trigger garage
            self._open_garage(garage_name)
            bot.sendMessage(chat_id=sender_id, text="{0} {1} garage...".format(action.capitalize() + 'ing', garage_name.capitalize()))
        else:
            bot.sendMessage(chat_id=sender_id, text="NO GARAGE FOUND. INVALID CODE")
            return 

        # Clear codes so there is no reuse
        self.garage_codes = {}

        def send_current_status(bot, job):
            text_to_send = "{0} status: {1}".format(garage_name.capitalize(), self._get_garage_position(garage_name))
            bot.sendMessage(chat_id=sender_id, text=text_to_send)

        # Wait to allow the door to move and send the status back
        self.job_queue.put(Job(send_current_status, 15.0, repeat=False))

    def setup(self):
        power_status_handler = CommandHandler('powerstatus', self.power_status, pass_args=True)
        self.dispatcher.add_handler(power_status_handler)

        acknowledge_alert_handler = CommandHandler('acknowledge', self.acknowledge_alert, pass_args=True)
        self.dispatcher.add_handler(acknowledge_alert_handler)


        # Handler for opening the garage
        garage_menu_handler = CommandHandler('garage', self.garage, pass_args=True)
        self.dispatcher.add_handler(garage_menu_handler)

        garage_menu_handler = CommandHandler('confirm', self.confirm_garage_action, pass_args=True)
        self.dispatcher.add_handler(garage_menu_handler)

        # Create the job to check if we have any nagios alerts to send
        send_alerts_job = Job(self.send_nagios_alerts, 90.0)
        self.job_queue.put(send_alerts_job, next_t=0.0)

    def run(self):
        self.setup()
        self.updater.start_polling()
        self.updater.idle()

if __name__ == '__main__':
    telegram_bot = TelegramBot()
    telegram_bot.run()

