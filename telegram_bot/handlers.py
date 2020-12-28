import logging

from telegram import Update
from telegram.ext import MessageHandler, Filters, CallbackContext

from telegram_bot.temperature_data import Temperatures
from .garage_door import GarageDoorHandler
from .market_quotes import CryptoQuotes

logger = logging.getLogger(__name__)


def setup_handlers(dispatcher):
    GarageDoorHandler().add_handlers(dispatcher)
    CryptoQuotes().add_handlers(dispatcher)
    Temperatures().add_handlers(dispatcher)

    # Add handler for messages we aren't handling
    dispatcher.add_handler(MessageHandler(Filters.private & (Filters.command | Filters.text), unknown_handler))


def unknown_handler(update: Update, context: CallbackContext):
    chat_id = update.effective_user.id
    logger.warning("UNHANDLED MESSAGE {}".format(update.to_dict()))

    context.bot.sendMessage(chat_id=chat_id, text="Did not understand message")
