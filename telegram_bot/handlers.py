import logging
import re

from telegram import InlineKeyboardMarkup, Update
from telegram.ext import MessageHandler, Filters, CallbackQueryHandler, CallbackContext

from telegram_bot.config_util import ConfigHelper
from telegram_bot.temperature_data import get_temperatures, get_temperature_chart
from .decorators import check_allowed_user
from .garage_door import GarageDoorHandler
from .market_quotes import CryptoQuotes

c = ConfigHelper()
logger = logging.getLogger(__name__)


def setup_handlers(dispatcher):
    # Handler for opening the garage
    dispatcher.add_handler(
        MessageHandler(
            Filters.private & (
                    Filters.regex(re.compile('^(Garage)', re.IGNORECASE)) |
                    Filters.regex(re.compile('^(Ga)', re.IGNORECASE),
                                  )),
            garage_actions_handler
        )
    )
    dispatcher.add_handler(CallbackQueryHandler(garage_actions_handler, pattern='^garage'))
    # END garage door handlers
    CryptoQuotes().add_handlers(dispatcher)

    dispatcher.add_handler(
        MessageHandler(
            Filters.private &
            Filters.regex(re.compile('^(charts)', re.IGNORECASE)),
            charts_handler
        )
    )

    dispatcher.add_handler(
        MessageHandler(
            Filters.private &
            Filters.regex(re.compile('^(temps)', re.IGNORECASE)),
            temperatures_handler
        )
    )

    #
    # Add handler for messages we aren't handling
    dispatcher.add_handler(MessageHandler(Filters.private & (Filters.command | Filters.text), unknown_handler))


# Action for operating the garage
@check_allowed_user
def garage_actions_handler(update: Update, context: CallbackContext):
    garage_handler = GarageDoorHandler()

    return_message = """"""
    sender_id = update.effective_user.id
    # Gives menu to select which garage to open
    if update.callback_query is None:
        logger.info("Got request to open garage from {}".format(sender_id))

        garage_statuses = garage_handler.get_garage_position()
        if not garage_statuses:
            context.bot.sendMessage(chat_id=sender_id, text='An exception occurred while getting garage status',
                                    reply_keyboard=None)
            return
        # Create the response message
        return_message += "Pick a garage:\n"
        return_message += garage_handler.status_to_string(garage_statuses)

        # create the keyboard
        keyboard_options = garage_handler.get_keyboard_format(garage_statuses)
        reply_keyboard = InlineKeyboardMarkup(keyboard_options, one_time_keyboard=True)
        context.bot.sendMessage(chat_id=sender_id, text=return_message, reply_markup=reply_keyboard)

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

        bot_admin = c.config['telegram']['bot_admin']
        if update.effective_user.id != bot_admin:
            context.bot.sendMessage(chat_id=bot_admin,
                                    text=f"{update.effective_user.first_name} has action={action} the garage")

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



@check_allowed_user
def temperatures_handler(update: Update, context: CallbackContext):
    try:
        msg = get_temperatures()
    except Exception as e:
        logger.exception("Error occurred getting temperatures")
        msg = "An error occurred while trying to get temperatures"

    chat_id = update.effective_user.id
    context.bot.sendMessage(chat_id=chat_id, text=msg)


@check_allowed_user
def charts_handler(update: Update, context: CallbackContext):
    chart_type_mapping = {'temps': get_temperature_chart}
    command_args = update.effective_message.text.lower().lstrip('charts ')
    chart_name = "temps" if not command_args else command_args

    chat_id = update.effective_user.id

    try:
        chart_url = chart_type_mapping[chart_name]()
    except Exception as e:
        msg = f"Error occurred getting {chart_name} chart"
        logger.exception(msg)
        context.bot.sendMessage(chat_id=chat_id, text=msg)
    else:
        context.bot.sendPhoto(chat_id=chat_id, photo=chart_url)


def unknown_handler(update: Update, context: CallbackContext):
    chat_id = update.effective_user.id
    logger.warning("UNHANDLED MESSAGE {}".format(update.to_dict()))

    context.bot.sendMessage(chat_id=chat_id, text="Did not understand message")
