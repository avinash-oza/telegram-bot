import logging
import os
from functools import wraps

logger = logging.getLogger(__name__)

#TODO: maybe a better way then env variables?
LIST_OF_ADMINS = [str(one_id) for one_id in os.environ.get('TELEGRAM_BOT_ADMINS', '').split(',')]

# adapted from telegram-bot snippets
def check_sender_admin(func):
    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        user_id = str(update.effective_user.id)
        if user_id not in LIST_OF_ADMINS:
            logger.error("User {} is not in the list of admins. Admins: {}".format(user_id, LIST_OF_ADMINS))
            bot.sendMessage(chat_id=user_id, text='Not authorized')
            return
        return func(_, bot, update, *args, **kwargs)
    return wrapped