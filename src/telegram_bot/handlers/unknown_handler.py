import logging

from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)


async def unknown_handler(update: Update, context: CallbackContext):
    chat_id = update.effective_user.id
    logger.warning("UNHANDLED MESSAGE {}".format(update.to_dict()))

    await context.bot.sendMessage(chat_id=chat_id, text="Did not understand message.")
