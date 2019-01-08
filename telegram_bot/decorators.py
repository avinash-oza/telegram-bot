import logging
from functools import wraps

logger = logging.getLogger(__name__)

#TODO: read this from the config
LIST_OF_ADMINS = []

# adapted from telegram-bot snippets
def check_sender_admin(func):
    @wraps(func)
    def wrapped(_, bot, update, *args, **kwargs):
        user_id = update.message.chat_id
        if user_id not in LIST_OF_ADMINS:
            logger.error("User {} is not in the list of admins".format(user_id))
            bot.sendMessage(chat_id=user_id, text='Not authorized')
            return
        return func(bot, update, *args, **kwargs)
    return wrapped