import ConfigParser
import logging
import subprocess
import time
import datetime
import mysql.connector
import os
import urlparse

import urllib
import json
from enum import Enum
from telegram.ext import Job, Updater, CommandHandler, MessageHandler, Filters, BaseFilter, ConversationHandler
from telegram.replykeyboardmarkup import ReplyKeyboardMarkup
from structlog import wrap_logger
from structlog.processors import JSONRenderer, TimeStamper, format_exc_info

from custom_filters import ConfirmFilter
from expiringdict import ExpiringDict
import requests

cache = ExpiringDict(max_len=10, max_age_seconds=15)
market_cap_cache = ExpiringDict(max_len=10, max_age_seconds=60*5) # 5 mins

#TODO: REMOVE THIS
auth = ('avi', 'milo')

# Declare states for garage door opening
class GarageConversationState(Enum):
    CONFIRM = 1


class TelegramBot(object):

    def __init__(self):
        self.garages = ['LEFT', 'RIGHT'] # TODO: read from config

        self.config = ConfigParser.ConfigParser()
        self.config.read('bot.config')
        self.updater = Updater(token=self.config.get('KEYS', 'bot_api'))
        self.dispatcher = self.updater.dispatcher
        self.job_queue = self.updater.job_queue
        self.key_to_alert_id_mapping = [] # Stores the list of keys that have been sent out at the latest alert
        self.garage_expire_request = None # job to handle expiring the codes if a garage is not selected
        self.logger = None
        self._init_logging()

    def _init_logging(self):
        log_file_path = os.path.join(self.config.get('ADMIN', 'log_file_location'), 'telegram-bot.log')
        logging.basicConfig(level=logging.INFO, format='%(message)s', filename=log_file_path)
        logger = logging.getLogger(__name__)

        self.logger = wrap_logger(logger, processors=[TimeStamper(), format_exc_info, JSONRenderer()], script="telegram_bot")

    def sender_is_admin(self, sender_id):
        sender_id = int(sender_id)
        admin_id = int(self.config.get('ADMIN', 'id'))
        if sender_id == admin_id:
            return True
        self.logger.warning("User {0} is not an admin".format(sender_id), sender_id=sender_id, admin_id=admin_id)
        return False

    def send_nagios_alerts(self, bot, job):
        """
        Retrieves alerts and sends them
        """
        # Before starting, clear out any alerts we were waiting for acknoledgement on
        self.key_to_alert_id_mapping[:] = []
        admin_id = self.config.get('ADMIN', 'id')
        self.logger.info("Getting alerts from db")

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
        if not total_count_of_alerts:
            return

        self.logger.info("Got {0} results".format(total_count_of_alerts))
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
            self.logger.debug("Update alert id {0} in the db for alerts".format(alert_id))
            # Send the message after we are sure the update occured
            message_str += alert_text
            # Add the alert to lists of alerts we can acknowledge along with a short string
            if notification_type == 'PROBLEM':
                self.key_to_alert_id_mapping.append((alert_id,"{0};{1}".format(host_name, service_name)))
            if index >= 4:
                # Send 5 messages together at a time and then wait till the next call
                break
            message_str += "--------------------\n"
            self.logger.info(alert_text)

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



            self.logger.info("Finished sending alerts")
        # Commit changes and close db
        conn.commit()
        conn.close()

    def power_status(self, bot, update, args):
        arguments_to_use = ['status', 'timeleft']
        complete_output = ""

        self.logger.info("Got request to check power status", sender_id=update.message.chat_id)
        for one_arg in arguments_to_use:
            command_to_run = ['/usr/lib/nagios/plugins/check_apcupsd {0}'.format(one_arg)]
            complete_output += subprocess.check_output(command_to_run, shell=True)

        bot.sendMessage(chat_id=update.message.chat_id, text=complete_output)
        self.logger.info("Sent message for power status", sender_id=update.message.chat_id)

    

    def acknowledge_alert(self, bot, update, args):
        """Takes the given alert and sends a request to acknowledge it.
        For now we just schedule 1 day of downtime so that it is not forgotten
        """
        self.logger.info("Got request to acknolwedge id {0}".format(args), sender_id=update.message.chat_id)
        if not args:
            # did not pass us an alert id
            bot.sendMessage(chat_id=update.message.chat_id, text="No alert specified")
            return

        try:
            alert_id, _ = self.key_to_alert_id_mapping[int(args[0])]
        except IndexError:
            # Some how the key they sent does not exist
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

    def _get_garage_position(self, garage_name='all'):
        # Returns whether the garage is open or closed
        request_url = 'http://172.16.2.102/garage/status/{0}'.format(garage_name)
        r = requests.get(request_url, auth=auth)
        if r.status_code == 200:
            return r.json()

        return []

    # Action for operating the garage
    def garage(self, bot, update, args):
        return_message = """"""
        sender_id = update.message.chat_id
        # Gives menu to select which garage to open
        if not self.sender_is_admin(sender_id):
            self.logger.warning("Unauthorized user", sender_id=sender_id)
            bot.sendMessage(chat_id=sender_id, text='Not authorized')
            return ConversationHandler.END

        options = [] # Stores the keys for the keyboard reply
        self.logger.info("Got request to open garage.", sender_id=sender_id)

        garage_statuses = self._get_garage_position()
        if not garage_statuses:
            bot.sendMessage(chat_id=sender_id, text='An exception occured while getting garage status', reply_keyboard=None)
            return ConversationHandler.END

        # Handle the reponse and creation of the keyboard
        return_message += "Pick a garage \n"
        for one_garage_dict in garage_statuses:
            garage_name = one_garage_dict['garage_name']
            current_status = one_garage_dict['status']
            return_message += ': '.join([garage_name, current_status, one_garage_dict['status_time']]) + '\n'
            
            # Determine whether this can be opened or closed
            if not one_garage_dict['error']: 
                action = 'CLOSE' if current_status == 'OPEN' else 'OPEN'
                key_string = ' '.join(['confirm', action, str(garage_name)])
                options.append([ key_string ]) # Store the key for the keyboard

        # Send the message with the keyboard
        reply_keyboard = ReplyKeyboardMarkup(options, one_time_keyboard=True)
        bot.sendMessage(chat_id=sender_id, text=return_message, reply_markup=reply_keyboard)

        # Expires request so that the conversation is not open forever
        def expire_request(bot, job):
            bot.sendMessage(chat_id=sender_id, text='Timeout reached. Please start again', reply_keyboard=None)
            return ConversationHandler.END

        # Add job to expire request
        self.garage_expire_request = Job(expire_request, 15.0, repeat=False)
        self.job_queue.put(self.garage_expire_request)

        # Set the conversation to go to the next state
        return GarageConversationState.CONFIRM

    def _open_garage(self, garage_name):
        # Actually invokes the code to open the garage
        command_to_run = ["ssh garage-door@pi2 'python ~/home-projects/pi-zero/relay_trigger.py {0}'".format(garage_name)]
        self.logger.info("START invoke code to trigger {0} garage".format(garage_name))
        try:
            _ =  subprocess.check_output(command_to_run, shell=True)
        except Exception as e:
            self.logger.exception("Exception when trying to open garage", exc_info=e,garage_name=garage_name)
        self.logger.info("FINISH invoke code to trigger {0} garage".format(garage_name))

    def confirm_garage_action(self, bot, update):
        sender_id = update.message.chat_id

        # See if there is a pending job to expire the request. Stop running it if there is
        if self.garage_expire_request is not None:
            self.garage_expire_request.schedule_removal()
            self.garage_expire_request = None

        if not self.sender_is_admin(update.message.chat_id):
            bot.sendMessage(chat_id=sender_id, text='Not authorized')
            return ConversationHandler.END

        action, garage_name = update.message.text.split(' ')[1:]
        request_url = 'http://172.16.2.102/garage/control/{0}/{1}'.format(garage_name, action)
        print(request_url)

        r = requests.get(request_url, auth=auth)
        if r.status_code != 200:
            bot.sendMessage(chat_id=sender_id, text='An exception occured while sending the {0} command'.format(action), reply_keyboard=None)
            return ConversationHandler.END

        response = r.json()


        self.logger.info("User triggered opening of garage", sender_id=sender_id, garage_name=garage_name)

        bot.sendMessage(chat_id=sender_id, text=response['status'])

        def send_current_status(bot, job):
            response = self._get_garage_position(garage_name)
            text_to_send = ': '.join([garage_name, response[0]['status'], response[0]['status_time']])

            bot.sendMessage(chat_id=sender_id, text=text_to_send)

        # Wait to allow the door to move and send the status back
        self.job_queue.put(Job(send_current_status, 15.0, repeat=False))

        return ConversationHandler.END

    def get_gemini_quote(self, quote_id):
        mapping = {"ETH" : "ethusd",
                   "BTC" : "btcusd"}
        quote_name = mapping[quote_id]

        GEMINI_STR = "GEMINI_STR"
        if cache.get(GEMINI_STR):
            self.logger.info("Got hit for cache", exchange='GEMINI')
            return cache.get(GEMINI_STR)

        url = 'https://api.gemini.com/v1/pubticker/{0}'.format(quote_name)
        try:
            result = json.load(urllib.urlopen(url))
        except Exception as e:
            self.logger.exception("Could not get quote from exchange", exc_info=e, exchange='GEMINI')
            return "Gemini", "", "Could not get quote from Gemini"

        bid_price = result['bid']
        ask_price = result['ask']

        quote_details = "Gemini", bid_price, ask_price

        # Store string into cache
        cache[GEMINI_STR] = quote_details
        
        return quote_details

    def get_gdax_quote(self, quote_name):
        GDAX_STR = "GDAX_STR"
        mapping = {"ETH" : "ETH-USD",
                   "BTC" : "BTC-USD"}

        quote_name = mapping[quote_name]
        if cache.get(GDAX_STR):
            self.logger.info("Got hit for cache", exchange='GDAX')
            return cache.get(GDAX_STR)

        url = 'https://api.gdax.com/products/{0}/book'.format(quote_name)
        try:
            result = json.load(urllib.urlopen(url))
        except Exception as e:
            self.logger.exception("Could not get quote from exchange", exc_info=e, exchange='GDAX')
            return "GDAX", "", "Could not get quote from GDAX"

        bid_price, bid_amount, _ = result['bids'][0]
        ask_price, ask_amount, _ = result['asks'][0]

        quote_details = "GDAX", bid_price, ask_price

        # Store string into cache
        cache[GDAX_STR] = quote_details
        
        return quote_details

    def get_coinmarketcap_data(self):
        COINMARKETCAP_STR = "COINMARKETCAP_STR"
        if market_cap_cache.get(COINMARKETCAP_STR):
            self.logger.info("Got hit for cache", exchange='COINMARKETCAP')
            return market_cap_cache.get(COINMARKETCAP_STR)

        url = 'https://api.coinmarketcap.com/v1/global/'
        try:
            result = json.load(urllib.urlopen(url))
        except Exception as e:
            self.logger.exception("Could not get quote from exchange", exc_info=e, exchange='COINMARKETCAP')
            return "CoinMarketCap", "", "Could not get info from CoinMarketCap"
        
        total_market_cap = result['total_market_cap_usd']
        bitcoin_percent_dominance = result['bitcoin_percentage_of_market_cap']

        # Get volume of ETH and BTC
        url = 'https://api.coinmarketcap.com/v1/ticker/{0}'
        tickers_to_get = ['bitcoin', 'ethereum']
        results = []

        for ticker in tickers_to_get:
            try:
                results.append(json.load(urllib.urlopen(url.format(ticker))))
            except Exception as e:
                self.logger.exception("Could not get quote from exchange", exc_info=e, exchange='COINMARKETCAP')
                return "CoinMarketCap", "", "Could not get info from CoinMarketCap"

        btc_result, ethereum_result = results
        btc_volume = btc_result[0]['24h_volume_usd']
        eth_volume = ethereum_result[0]['24h_volume_usd']
        eth_btc_volume_ratio = float(eth_volume)/float(btc_volume)

        final_result = (total_market_cap, bitcoin_percent_dominance, eth_btc_volume_ratio)

        market_cap_cache[COINMARKETCAP_STR] = final_result

        return final_result

    def get_current_quotes(self, bot, update, args):
        chat_id = update.message.chat_id

        if not self.sender_is_admin(chat_id):
            bot.sendMessage(chat_id=chat_id, text='Not authorized')
            return ConversationHandler.END

        quote_name = "ETH" if not args else str(args[0])

        prices_to_get = [self.get_gdax_quote, self.get_gemini_quote]
        string_to_send = "Time: {0}\n".format(datetime.datetime.today().strftime("%Y-%m-%d %H:%m:%S"))

        for one_exchange in prices_to_get:
            exchange_name, bid_price, ask_price = one_exchange(quote_name)
            string_to_send += "{0} : Bid: {1} Ask: {2}\n".format(exchange_name, bid_price, ask_price)

        total_marketcap, btc_dominance, eth_btc_volume_ratio = self.get_coinmarketcap_data()

        string_to_send += "MarketCap: {0:d}B BTC Dom: {1} ETH/BTC Vol Ratio:{2:.2f}".format(int(total_marketcap/1000000000), btc_dominance, eth_btc_volume_ratio)

        self.logger.info("Sending quote: {0}".format(string_to_send), sender_id=chat_id, exchange='GDAX')
        bot.sendMessage(chat_id=chat_id, text=string_to_send)
        return ConversationHandler.END

    def unknown_handler(self, bot, update):
        if update.message:
            chat_id = update.message.chat_id
        else:
            chat_id = update.channel.chat_id
        self.logger.warn("UNHANDLED MESSAGE".format(update.message.chat_id), sender_id=chat_id, message_dict=update.to_dict())

        bot.sendMessage(chat_id=chat_id, text="Did not understand message")

        return ConversationHandler.END # Make sure to end any conversations

    def setup(self):
        self.logger.info("Starting up TelegramBot")

        power_status_handler = CommandHandler('powerstatus', self.power_status, pass_args=True)
        self.dispatcher.add_handler(power_status_handler)

        acknowledge_alert_handler = CommandHandler('acknowledge', self.acknowledge_alert, pass_args=True)
        self.dispatcher.add_handler(acknowledge_alert_handler)

        # Handler for opening the garage
        garage_menu_handler = ConversationHandler(
                entry_points = [CommandHandler('garage', self.garage, pass_args=True)],
                states= {
                    GarageConversationState.CONFIRM: [MessageHandler(ConfirmFilter(), self.confirm_garage_action)]
                    },
                fallbacks=[MessageHandler(Filters.command | Filters.text, self.unknown_handler)]
                )
        self.dispatcher.add_handler(garage_menu_handler)

        # GDAX quote handler
        gdax_quote_handler=CommandHandler('quotes', self.get_current_quotes, pass_args=True)
        self.dispatcher.add_handler(gdax_quote_handler)


        # Add handler for messages we arent handling
        unknown_handler = MessageHandler(Filters.command | Filters.text, self.unknown_handler)
        self.dispatcher.add_handler(unknown_handler)


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

