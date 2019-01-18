import configparser
import logging
import subprocess
import time
from enum import Enum

import requests
from expiringdict import ExpiringDict
from telegram import InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, RegexHandler, \
    CallbackQueryHandler
from telegram.replykeyboardmarkup import ReplyKeyboardMarkup

from .decorators import check_sender_admin
from .garage_door import GarageDoorHandler
from .market_quotes import get_current_quotes

acknowledgeable_alerts_cache = ExpiringDict(max_len=6, max_age_seconds=180) # max alerts at a time is 3 mins

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) #TODO: Remove this later on

GARAGE_CONFIRMED_STATE = 1


class TelegramBot(object):

    def __init__(self, config_file='bot.config'):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        self.updater = Updater(token=self.config.get('KEYS', 'bot_api'))
        self.dispatcher = self.updater.dispatcher
        self.job_queue = self.updater.job_queue
        self.garage_expire_request = None # job to handle expiring the codes if a garage is not selected
        # Garage door params
        self.garage_handler = GarageDoorHandler(self.config)

    def send_nagios_alerts(self, bot, job):
        """
        Retrieves alerts and sends them
        """
        admin_id = self.config.get('ADMIN', 'id')
        logger.info("Getting alerts from db")

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

        logger.info("Finished sending {} alerts".format(len(unsent_alerts)))

    def power_status(self, bot, update, args):
        arguments_to_use = ['status', 'timeleft']
        complete_output = ""

        logger.info("Got request to check power status", sender_id=update.message.chat_id)
        for one_arg in arguments_to_use:
            command_to_run = ['/usr/lib/nagios/plugins/check_apcupsd {0}'.format(one_arg)]
            complete_output += subprocess.check_output(command_to_run, shell=True)

        bot.sendMessage(chat_id=update.message.chat_id, text=complete_output)
        logger.info("Sent message for power status", sender_id=update.message.chat_id)


    def acknowledge_alert(self, bot, update, groups):
        """
        Given a string in the form of "acknowledge <ID> | <SOME DESC>" this sends the appropriate nagios commands
        :param bot:
        :param update:
        :param groups: tuple of regex group
        :return:
        """
        sender_id = update.message.chat_id
        logger.info("Got request to acknowledge id {0}".format(groups, sender_id=sender_id))
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
            logger.error("Attempted to access id {}. Cache had {}".format(alert_id, acknowledgeable_alerts_cache))
            return ConversationHandler.END

        hostname = self.config.get('ALERTS', 'hostname')
        url = 'http://{0}/acknowledge/{1}'.format(hostname, alert_id)
        r = requests.get(url)
        if r.status_code != 200:
            bot.sendMessage(chat_id=sender_id, text='An exception occured while acknowledging alert', reply_keyboard=None)
            return ConversationHandler.END

        text = "Successfully scheduled downtime for id {0} for 1 day".format(alert_id)
        logger.info(text)
        bot.sendMessage(chat_id=sender_id, text=text, reply_keyboard=None)

        return ConversationHandler.END

    # Action for operating the garage
    @check_sender_admin
    def garage(self, bot, update):
        return_message = """"""
        sender_id = update.effective_user.id
        # Gives menu to select which garage to open
        if update.callback_query is None:
            logger.info("Got request to open garage from {}".format(sender_id))

            garage_statuses = self.garage_handler.get_garage_position()
            if not garage_statuses:
                bot.sendMessage(chat_id=sender_id, text='An exception occured while getting garage status',
                                reply_keyboard=None)
                return ConversationHandler.END

            # Create the response message
            return_message += "Pick a garage:\n"
            return_message += self.garage_handler.status_to_string(garage_statuses)

            # create the keyboard
            keyboard_options = self.garage_handler.get_keyboard_format(garage_statuses)
            reply_keyboard = InlineKeyboardMarkup(keyboard_options, one_time_keyboard=True)
            bot.sendMessage(chat_id=sender_id, text=return_message, reply_markup=reply_keyboard)

            # Set the conversation to go to the next state
            return GARAGE_CONFIRMED_STATE


        if update.callback_query is not None:
            update.callback_query.answer()
            action_and_garage = update.callback_query.data
            if action_and_garage == 'garage cancel':
                update.callback_query.edit_message_text('Not doing anything')
                return ConversationHandler.END

            # process a confirm action
            action, garage = action_and_garage.lstrip('garage ').split(' ')
            logger.warning("Got confirmation for triggering garage: {} and action: {}".format(garage, action))

            update.callback_query.edit_message_text('Triggering the {} garage to {}'.format(garage.capitalize(), action.lower()))
            r = self.garage_handler.control_garage(garage, action)

            if not len(r):
                update.callback_query.edit_message_text("An error occured while trying to trigger the garage.")
                return ConversationHandler.END

            # check for any errors in triggering
            if any([resp['error'] for resp in r]):
                # join the errors together
                update.callback_query.edit_message_text('|'.join(resp['message'] for resp in r))
                return ConversationHandler.END

            # No errors

            logger.info("User triggered opening of garage sender_id={} garage_name={}".format(sender_id, garage))
            # update.callback_query.edit_message_text( '|'.join(resp['message'] for resp in r))
            time.sleep(2)
            update.callback_query.edit_message_text('Waiting 10 seconds before refreshing...')

            # Wait 10s and send another status response, wait 10s and then send the reply
            time.sleep(10)
            garage_statuses = self.garage_handler.get_garage_position()

            # Create the response message
            return_message = "Status after {} on the {} garage:\n".format(action, garage)
            return_message += self.garage_handler.status_to_string(garage_statuses)

            update.callback_query.edit_message_text(return_message)

            return ConversationHandler.END

    @check_sender_admin
    def get_current_quotes(self, bot, update, args):
        quote_name = "ETH" if not args else str(args[0])
        quotes_response = get_current_quotes(quote_name)
        chat_id = update.effective_user.id
        bot.sendMessage(chat_id=chat_id, text=quotes_response)
        return ConversationHandler.END

    def unknown_handler(self, bot, update):
        if update.message:
            chat_id = update.message.chat_id
        else:
            chat_id = update.channel.chat_id
        logger.warning("UNHANDLED MESSAGE {}".format(update.to_dict()))

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
        logger.info("Starting up TelegramBot")

        power_status_handler = CommandHandler('powerstatus', self.power_status, pass_args=True)
        self.dispatcher.add_handler(power_status_handler)

        acknowledge_alert_handler = RegexHandler('^(acknowledge \d+)', self.acknowledge_alert, pass_groups=True)
        self.dispatcher.add_handler(acknowledge_alert_handler)

        # Handler for opening the garage
        garage_menu_handler = ConversationHandler(
                entry_points = [CommandHandler('garage', self.garage),
                                RegexHandler('^(Garage|garage)', self.garage),
                                RegexHandler('^(Ga)', self.garage)],
                states= {GARAGE_CONFIRMED_STATE: [CallbackQueryHandler(self.garage, pattern='^garage')]},
                fallbacks=[MessageHandler(Filters.command | Filters.text, self.unknown_handler)],
            conversation_timeout=15
                )
        self.dispatcher.add_handler(garage_menu_handler)

        crypto_quotes_handler = CommandHandler('quotes', self.get_current_quotes, pass_args=True)
        self.dispatcher.add_handler(crypto_quotes_handler)


        # Add handler for messages we arent handling
        unknown_handler = MessageHandler(Filters.command | Filters.text, self.unknown_handler)
        self.dispatcher.add_handler(unknown_handler)

        # def startup_alert(bot, job):
        #     admin_id = int(self.config.get('ADMIN', 'id'))
        #     bot.sendMessage(chat_id=admin_id, text='Bot started up')
        #
        # self.job_queue.run_once(startup_alert, 10)
        # Create the job to check if we have any nagios alerts to send
        # TODO: Enable this once fixed
        # self.job_queue.run_repeating(self.send_nagios_alerts, 90.0)
        # TODO: Enable this once fixed
        # Add job to alert nagios server we are up
        # if int(self.config.get('ALERTS', 'heartbeat')) == 1:
        #     logger.info("Enabling heartbeat handler for nagios")
        #     self.job_queue.run_repeating(self.heartbeat_handler, 120.0)

    def run(self):
        self.setup()
        self.updater.start_polling()
        self.updater.idle()


