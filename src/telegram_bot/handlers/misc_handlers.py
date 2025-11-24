import logging
import re

from telegram import Update
from telegram.ext import CallbackContext, MessageHandler, filters

from telegram_bot import __version__
from telegram_bot.handlers.handler_base import HandlerBase

logger = logging.getLogger(__name__)

__all__ = ["VersionHandler", "unknown_handler"]


class VersionHandler(HandlerBase):
    async def _handle_message(self, update: Update, context: CallbackContext):
        response = f"The version is {__version__}"

        chat_id = update.effective_user.id
        await context.bot.sendMessage(
            chat_id=chat_id, text=response, parse_mode="Markdown"
        )

    def _get_handlers(self):
        return [
            (
                MessageHandler,
                {
                    "filters": filters.ChatType.PRIVATE
                    & filters.Regex(re.compile("^(version)", re.IGNORECASE)),
                    "callback": self._handle_message,
                },
            )
        ]


async def unknown_handler(update: Update, context: CallbackContext):
    chat_id = update.effective_user.id
    logger.warning("UNHANDLED MESSAGE {}".format(update.to_dict()))

    await context.bot.sendMessage(chat_id=chat_id, text="Did not understand message")
