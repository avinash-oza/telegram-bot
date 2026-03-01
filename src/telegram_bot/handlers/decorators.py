import logging
from functools import wraps

from telegram import Update
from telegram.ext import ConversationHandler

from telegram_bot.config_helper import ConfigHelper

c = ConfigHelper()
logger = logging.getLogger(__name__)

ALLOWED_USERS = [str(s) for s in c.get("telegram", "allowed_users")]


# adapted from telegram-bot snippets


def check_allowed_user(func):
    """Decorator for standalone callbacks (non-instance methods)."""

    @wraps(func)
    async def wrapped(update: Update, context, *args, **kwargs):
        user_id = str(update.effective_user.id)
        if user_id not in ALLOWED_USERS:
            logger.error(f"User {user_id} is not in the allowed users list")
            await context.bot.send_message(chat_id=user_id, text="Not authorized")
            return ConversationHandler.END  # for ConversationHandlers
        return await func(update, context, *args, **kwargs)

    return wrapped
