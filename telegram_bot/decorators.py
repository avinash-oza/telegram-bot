import logging
from functools import wraps

from telegram_bot.config_util import ConfigHelper

c = ConfigHelper()
logger = logging.getLogger(__name__)

LIST_OF_ADMINS = [str(s) for s in c.get('telegram', 'bot_admins')]


# adapted from telegram-bot snippets
def check_sender_admin(func):
    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        user_id = str(update.effective_user.id)
        if user_id not in LIST_OF_ADMINS:
            logger.error("User {} is not in the list of admins. Admins: {}".format(user_id, LIST_OF_ADMINS))
            bot.sendMessage(chat_id=user_id, text='Not authorized')
            return
        return func(bot, update, *args, **kwargs)

    return wrapped
