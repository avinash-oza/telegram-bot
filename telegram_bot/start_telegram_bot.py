import logging
import os
import time

from telegram import InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, RegexHandler, \
    CallbackQueryHandler

from .decorators import check_sender_admin
from .garage_door import GarageDoorHandler
from .market_quotes import get_current_quotes

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  #TODO: Remove this later on

GARAGE_CONFIRMED_STATE = 1


class TelegramBot(object):

    def __init__(self):
        self.updater = Updater(token=os.environ['TELEGRAM_BOT_API_KEY'])
        self.dispatcher = self.updater.dispatcher
        self.job_queue = self.updater.job_queue
        # Garage door params
        self.garage_handler = GarageDoorHandler()

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

    def setup(self):
        logger.info("Starting up TelegramBot")

        # Handler for opening the garage
        garage_menu_handler = ConversationHandler(
            entry_points=[CommandHandler('garage', self.garage),
                          RegexHandler('^(Garage|garage)', self.garage),
                          RegexHandler('^(Ga)', self.garage)],
            states={GARAGE_CONFIRMED_STATE: [CallbackQueryHandler(self.garage, pattern='^garage')]},
            fallbacks=[MessageHandler(Filters.command | Filters.text, self.unknown_handler)],
            conversation_timeout=15
        )
        self.dispatcher.add_handler(garage_menu_handler)

        crypto_quotes_handler = CommandHandler('quotes', self.get_current_quotes, pass_args=True)
        self.dispatcher.add_handler(crypto_quotes_handler)

        # Add handler for messages we arent handling
        unknown_handler = MessageHandler(Filters.command | Filters.text, self.unknown_handler)
        self.dispatcher.add_handler(unknown_handler)

    def run(self):
        self.setup()
        self.updater.start_polling()
        self.updater.idle()


# @check_sender_admin
def get_current_quotes_handler(bot, update, args):
    quote_name = "ETH" if not args else str(args[0])
    quotes_response = get_current_quotes(quote_name)
    chat_id = update.effective_user.id
    bot.sendMessage(chat_id=chat_id, text=quotes_response)
    return ConversationHandler.END


def setup_handlers(dispatcher):
    dispatcher.add_handler(CommandHandler('quotes', get_current_quotes_handler,  pass_args=True))
