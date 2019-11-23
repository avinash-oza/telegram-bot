import logging
import time

from telegram import InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, Filters, RegexHandler, \
    CallbackQueryHandler

from .decorators import check_sender_admin
from .garage_door import GarageDoorHandler
from .market_quotes import get_current_quotes

logger = logging.getLogger(__name__)

garage_handler = GarageDoorHandler()

# Action for operating the garage
@check_sender_admin
def garage_actions_handler(bot, update):
    return_message = """"""
    sender_id = update.effective_user.id
    # Gives menu to select which garage to open
    if update.callback_query is None:
        logger.info("Got request to open garage from {}".format(sender_id))

        garage_statuses = garage_handler.get_garage_position()
        if not garage_statuses:
            bot.sendMessage(chat_id=sender_id, text='An exception occurred while getting garage status',
                            reply_keyboard=None)
            return

        # Create the response message
        return_message += "Pick a garage:\n"
        return_message += garage_handler.status_to_string(garage_statuses)

        # create the keyboard
        keyboard_options = garage_handler.get_keyboard_format(garage_statuses)
        reply_keyboard = InlineKeyboardMarkup(keyboard_options, one_time_keyboard=True)
        bot.sendMessage(chat_id=sender_id, text=return_message, reply_markup=reply_keyboard)

        return

    if update.callback_query is not None:
        update.callback_query.answer()
        action_and_garage = update.callback_query.data
        if action_and_garage == 'garage cancel':
            logger.info("Cancelled request to open garage")
            update.callback_query.edit_message_text('Not doing anything')
            return

        # process a confirm action
        action, garage = action_and_garage.lstrip('garage ').split(' ')
        logger.warning("Got confirmation for triggering garage: {} and action: {}".format(garage, action))

        update.callback_query.edit_message_text('Triggering the {} garage to {}'.format(garage.capitalize(), action.lower()))
        r = garage_handler.control_garage(garage, action)

        if not r:
            update.callback_query.edit_message_text("An error occurred while trying to trigger the garage.")
            return

        # check for any errors in triggering
        if any([resp['error'] for resp in r]):
            # join the errors together
            update.callback_query.edit_message_text('|'.join(resp['message'] for resp in r))
            return

        # No errors

        logger.info("User triggered opening of garage sender_id={} garage_name={}".format(sender_id, garage))
        # update.callback_query.edit_message_text( '|'.join(resp['message'] for resp in r))
        time.sleep(2)
        update.callback_query.edit_message_text('Waiting 10 seconds before refreshing...')

        # Wait 10s and send another status response, wait 10s and then send the reply
        time.sleep(10)
        garage_statuses = garage_handler.get_garage_position()

        # Create the response message
        return_message = "Status after {} on the {} garage:\n".format(action, garage)
        return_message += garage_handler.status_to_string(garage_statuses)

        update.callback_query.edit_message_text(return_message)

        return

@check_sender_admin
def get_current_quotes_handler(bot, update, args):
    quote_name = "ETH" if not args else str(args[0])
    logger.info(f"Got request for {quote_name}")
    quotes_response = get_current_quotes(quote_name)
    chat_id = update.effective_user.id
    bot.sendMessage(chat_id=chat_id, text=quotes_response)

def unknown_handler(bot, update):
    chat_id = update.effective_user.id
    logger.warning("UNHANDLED MESSAGE {}".format(update.to_dict()))

    bot.sendMessage(chat_id=chat_id, text="Did not understand message")


def setup_handlers(dispatcher):
    # Handler for opening the garage
    for s in ['garage', '^(Garage|garage)', '^(Ga)', '^(ga)']:
        dispatcher.add_handler(RegexHandler(s, garage_actions_handler))

    dispatcher.add_handler(CallbackQueryHandler(garage_actions_handler, pattern='^garage'))
    # END garage door handlers

    dispatcher.add_handler(CommandHandler('quotes', get_current_quotes_handler,  pass_args=True))

    # Add handler for messages we aren't handling
    dispatcher.add_handler(MessageHandler(Filters.command | Filters.text, unknown_handler))
