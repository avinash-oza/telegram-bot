import logging

from telegram import InlineKeyboardMarkup
from telegram.ext import MessageHandler, Filters, RegexHandler, \
    CallbackQueryHandler

from telegram_bot.temperature_data import get_temperatures, get_temperature_chart
from .decorators import check_sender_admin
from .garage_door import GarageDoorHandler
from .market_quotes import get_current_quotes

logger = logging.getLogger(__name__)


def setup_handlers(dispatcher):
    # Handler for opening the garage
    for s in ['garage', '^(Garage|garage)', '^(Ga)', '^(ga)']:
        dispatcher.add_handler(RegexHandler(s, garage_actions_handler))

    dispatcher.add_handler(CallbackQueryHandler(garage_actions_handler, pattern='^garage'))
    # END garage door handlers

    dispatcher.add_handler(RegexHandler('^([Qq]uotes)', get_current_quotes_handler))
    dispatcher.add_handler(RegexHandler('^([Cc]harts)', charts_handler))
    for s in ['^([Tt]emp)', '^([Tt]emps)']:
        dispatcher.add_handler(RegexHandler(s, temperatures_handler))

    # Add handler for messages we aren't handling
    dispatcher.add_handler(MessageHandler(Filters.command | Filters.text, unknown_handler))


# Action for operating the garage
@check_sender_admin
def garage_actions_handler(bot, update):
    garage_handler = GarageDoorHandler()

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

        update.callback_query.edit_message_text(
            'Triggering the {} garage to {}'.format(garage.capitalize(), action.lower()))
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

        update.callback_query.edit_message_text('Triggered garage, check status separately')

        return


@check_sender_admin
def get_current_quotes_handler(bot, update):
    command_args = update.effective_message.text.lower().lstrip('quotes ')
    quote_name = "ETH" if not command_args else command_args
    logger.info(f"Got request for {quote_name}")
    try:
        quotes_response = get_current_quotes(quote_name)
    except Exception as e:
        quotes_response = "Error occured getting quotes"
    chat_id = update.effective_user.id
    bot.sendMessage(chat_id=chat_id, text=quotes_response)


@check_sender_admin
def temperatures_handler(bot, update):
    try:
        msg = get_temperatures()
    except Exception as e:
        logger.exception("Error occured getting temperatures")
        msg = "An error occurred while trying to get temperatures"

    chat_id = update.effective_user.id
    bot.sendMessage(chat_id=chat_id, text=msg)


@check_sender_admin
def charts_handler(bot, update):
    chart_type_mapping = {'temps': get_temperature_chart}
    command_args = update.effective_message.text.lower().lstrip('charts ')
    chart_name = "temps" if not command_args else command_args

    chat_id = update.effective_user.id

    try:
        chart_url = chart_type_mapping[chart_name]()
    except Exception as e:
        msg = f"Error occurred getting {chart_name} chart"
        logger.exception(msg)
        bot.sendMessage(chat_id=chat_id, text=msg)
    else:
        bot.sendPhoto(chat_id=chat_id, photo=chart_url)


def unknown_handler(bot, update):
    chat_id = update.effective_user.id
    logger.warning("UNHANDLED MESSAGE {}".format(update.to_dict()))

    bot.sendMessage(chat_id=chat_id, text="Did not understand message")
