import configparser
import logging
import subprocess
import time
import datetime
import mysql.connector
import os
import urllib.parse

import urllib.request, urllib.parse, urllib.error
import json
from enum import Enum
from telegram.ext import Job, Updater, CommandHandler, MessageHandler, Filters, BaseFilter, ConversationHandler, RegexHandler
from telegram.replykeyboardmarkup import ReplyKeyboardMarkup
from structlog import wrap_logger
from structlog.processors import JSONRenderer, TimeStamper, format_exc_info

from custom_filters import ConfirmFilter
from expiringdict import ExpiringDict
import requests

cache = ExpiringDict(max_len=10, max_age_seconds=15)
market_cap_cache = ExpiringDict(max_len=10, max_age_seconds=60*5) # 5 mins
acknowledgeable_alerts_cache = ExpiringDict(max_len=6, max_age_seconds=180) # max alerts at a time is 3 mins

# Declare states for garage door opening
class GarageConversationState(Enum):
    CONFIRM = 1


class TelegramBot(object):

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('bot.config')
        self.updater = Updater(token=self.config.get('KEYS', 'bot_api'))
        self.dispatcher = self.updater.dispatcher
        self.job_queue = self.updater.job_queue
        self.garage_expire_request = None # job to handle expiring the codes if a garage is not selected
        self.logger = None
        self._init_logging()
        # Garage door params
        self.garage_door_base_url = None
        self.garage_door_user_pass = None
        self._set_garage_door_parameters()

    def _set_garage_door_parameters(self):
        hostname = self.config.get('GARAGE', 'hostname')
        port = self.config.get('GARAGE', 'port')

        user = self.config.get('GARAGE', 'username')
        password = self.config.get('GARAGE', 'password')

        self.garage_door_base_url = 'http://{0}:{1}'.format(hostname, port)
        self.garage_door_user_pass = (user, password)

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
        admin_id = self.config.get('ADMIN', 'id')
        self.logger.info("Getting alerts from db")

        hostname = self.config.get('ALERTS', 'hostname')
        url = 'http://{0}/get_nagios_unsent_alerts'.format(hostname)
        r = requests.get(url)
        if r.status_code != 200:
            bot.sendMessage(chat_id=sender_id, text='An exception occured while acknowledging alert', reply_keyboard=None)
            return ConversationHandler.END

        unsent_alerts = r.json()
        if not unsent_alerts: # Nothing to do
            return ConversationHandler.END


        message_str = """"""
        for one_alert in unsent_alerts: # No need to check count as server limits it

            alert_id = one_alert['id']
            url = 'http://{0}/update_alert/{1}/SENT'.format(hostname, alert_id)
            r = requests.get(url)
            if r.status_code != 200:
                bot.sendMessage(chat_id=sender_id, text='An exception occured while updating alert status', reply_keyboard=None)

            host_name = one_alert['hostname']
            service_name = one_alert['hostname']
            message_str += "Alert ID: {}".format(str(one_alert['id'])) 
            message_str += one_alert['message_text']
            if one_alert['acknowledgable']:
                acknowledgeable_alerts_cache[alert_id] = (host_name, service_name) # Add to dictionary to track
            message_str += "--------------------\n"

        if message_str:
            message_str += "{0} messages sent".format(len(unsent_alerts))

        # If there are alerts than can be acknowledged, add the keyboard to acknowledge
        reply_keyboard = None
        if acknowledgeable_alerts_cache: # We have some alerts that can be acknowledged
            options = []  # Stores the keys for the keyboard reply
            for alert_id, (host, service) in list(acknowledgeable_alerts_cache.items()):
                key_string = "acknowledge {alert_id} | {host}  {service}".format(alert_id=alert_id, host=host, service=service)
                options.append([ key_string ]) # Store the key for the keyboard

            # Send the message with the keyboard
            reply_keyboard = ReplyKeyboardMarkup(options, one_time_keyboard=True)
        bot.sendMessage(chat_id=admin_id, text=message_str, reply_markup=reply_keyboard)

        self.logger.info("Finished sending {} alerts".format(len(unsent_alerts)))

    def power_status(self, bot, update, args):
        arguments_to_use = ['status', 'timeleft']
        complete_output = ""

        self.logger.info("Got request to check power status", sender_id=update.message.chat_id)
        for one_arg in arguments_to_use:
            command_to_run = ['/usr/lib/nagios/plugins/check_apcupsd {0}'.format(one_arg)]
            complete_output += subprocess.check_output(command_to_run, shell=True)

        bot.sendMessage(chat_id=update.message.chat_id, text=complete_output)
        self.logger.info("Sent message for power status", sender_id=update.message.chat_id)

    

    def acknowledge_alert(self, bot, update, groups):
        """
        Given a string in the form of "acknowledge <ID> | <SOME DESC>" this sends the appropriate nagios commands
        :param bot:
        :param update:
        :param groups: tuple of regex group
        :return:
        """
        sender_id = update.message.chat_id
        self.logger.info("Got request to acknowledge id {0}".format(groups, sender_id=sender_id))
        if not groups:
            # did not pass us an alert id
            bot.sendMessage(chat_id=update.message.chat_id, text="No alert specified")
            return ConversationHandler.END

        try:
            _, alert_id = groups[0].split(' ')
            alert_id = alert_id.strip()
        except IndexError:
             bot.sendMessage(chat_id=update.message.chat_id, text="Invalid string {} passed to acknowledge".format(groups[0]))
             return ConversationHandler.END

        if alert_id not in acknowledgeable_alerts_cache:
            bot.sendMessage(chat_id=update.message.chat_id, text="Did not find id {} in cache".format(groups[0]))
            self.logger.error("Attempted to access id {}. Cache had {}".format(alert_id, acknowledgeable_alerts_cache))
            return ConversationHandler.END

        hostname = self.config.get('ALERTS', 'hostname')
        url = 'http://{0}/acknowledge/{1}'.format(hostname, alert_id)
        r = requests.get(url)
        if r.status_code != 200:
            bot.sendMessage(chat_id=sender_id, text='An exception occured while acknowledging alert', reply_keyboard=None)
            return ConversationHandler.END

        text = "Successfully scheduled downtime for id {0} for 1 day".format(alert_id)
        self.logger.info(text)
        bot.sendMessage(chat_id=sender_id, text=text, reply_keyboard=None)

        return ConversationHandler.END

    def _get_garage_position(self, garage_name='all'):
        # Returns whether the garage is open or closed
        request_url = '{0}/garage/status/{1}'.format(self.garage_door_base_url, garage_name)
        r = requests.get(request_url, auth=self.garage_door_user_pass)
        if r.status_code == 200:
            return r.json()

        return []

    # Action for operating the garage
    def garage(self, bot, update):
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
        options.append(["CANCEL GARAGE"]) # Store the key for the keyboard

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
        request_url = '{0}/garage/control/{1}/{2}'.format(self.garage_door_base_url, garage_name, action)

        r = requests.get(request_url, auth=self.garage_door_user_pass)
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
            result = json.load(urllib.request.urlopen(url))
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
            result = json.load(urllib.request.urlopen(url))
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
            result = json.load(urllib.request.urlopen(url))
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
                results.append(json.load(urllib.request.urlopen(url.format(ticker))))
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

    def heartbeat_handler(self, bot, update):
        # Sents a signal to the nagios server that we are still up
        dict_to_send = [{'return_code': "0",
                        'plugin_output': "Telegram bot is up",
                        'service_description': "Telegram Bot Available",
                        'hostname': 'monitoring-station',
                        }]
        url = self.config.get('ALERTS', 'passive_alerts_endpoint')

        requests.post(url, json=dict_to_send)

    def setup(self):
        self.logger.info("Starting up TelegramBot")

        power_status_handler = CommandHandler('powerstatus', self.power_status, pass_args=True)
        self.dispatcher.add_handler(power_status_handler)

        acknowledge_alert_handler = RegexHandler('^(acknowledge \d+)', self.acknowledge_alert, pass_groups=True)
        self.dispatcher.add_handler(acknowledge_alert_handler)

        # Handler for opening the garage
        garage_menu_handler = ConversationHandler(
                entry_points = [CommandHandler('garage', self.garage),
                                RegexHandler('^(Garage|garage)', self.garage),
                                RegexHandler('^(Ga)', self.garage)],
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

        # Add job to alert nagios server we are up
        if int(self.config.get('ALERTS', 'heartbeat')) == 1:
            self.logger.info("Enabling heartbeat handler for nagios")
            heartbeat_job = Job(self.heartbeat_handler, 120.0)
            self.job_queue.put(heartbeat_job, next_t=0.0)

    def run(self):
        self.setup()
        self.updater.start_polling()
        self.updater.idle()

if __name__ == '__main__':
    telegram_bot = TelegramBot()
    telegram_bot.run()

