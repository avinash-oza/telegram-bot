import json
import logging

import telegram
from telegram import Update
from telegram.ext import Dispatcher
from telegram.ext import MessageHandler, Filters, CallbackContext

from telegram_bot.config_util import ConfigHelper
from telegram_bot.handlers.garage_door import GarageDoorHandler
from telegram_bot.handlers.market_quotes import CryptoQuotes
from telegram_bot.handlers.temperature_data import Temperatures

c = ConfigHelper()

if len(logging.getLogger().handlers) > 0:
    # The Lambda environment pre-configures a handler logging to stderr. If a handler is already configured,
    # `.basicConfig` does not execute. Thus we set the level directly.
    logging.getLogger().setLevel(logging.INFO)
else:
    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

logger = logging.getLogger()

OK_RESPONSE = {
    'statusCode': 200,
    'headers': {'Content-Type': 'application/json'},
    'body': json.dumps('ok')
}
ERROR_RESPONSE = {
    'statusCode': 400,
    'body': json.dumps('Oops, something went wrong!')
}


def webhook(event, context):
    """
    Runs the Telegram webhook.
    """

    bot = _configure_telegram()
    dispatcher = Dispatcher(bot, None, workers=0)

    setup_handlers(dispatcher)

    logger.info('Event: {}'.format(event))

    if event.get('httpMethod') == 'POST' and event.get('body'):
        logger.info('Message received')
        update = telegram.Update.de_json(json.loads(event.get('body')), bot)
        chat_id = update.effective_user
        text = update.effective_message

        dispatcher.process_update(update)

        logger.info(f"chat_id={chat_id}, TEXT:{text}")
        logger.info('Message sent')

    elif event.get('httpMethod') == 'GET' and event.get('path') == '/setWebHook':
        logger.info("Setting webhook")
        _set_webhook(event, context, bot)

    return OK_RESPONSE


def _configure_telegram():
    """
    Configures the bot with a Telegram Token.

    Returns a bot instance.
    """

    TELEGRAM_TOKEN = c.get('telegram', 'api_key')
    if not TELEGRAM_TOKEN:
        msg = 'The TELEGRAM_BOT_API_KEY must be set'
        logger.error(msg)
        raise RuntimeError(msg)

    bot = telegram.Bot(TELEGRAM_TOKEN)

    return bot


def _set_webhook(event, context, bot):
    """
    Sets the Telegram bot webhook.
    """

    logger.info('Got request to set webhook')
    logger.info(f'EVENT: {event}')

    url = f"https://{event.get('headers').get('Host')}/"

    logger.info(f'Setting webhook url={url}')
    webhook = bot.set_webhook(url)

    if webhook:
        logger.info(f'Successfully set webhook')
        return OK_RESPONSE

    return ERROR_RESPONSE


def setup_handlers(dispatcher):
    GarageDoorHandler().add_handlers(dispatcher)
    CryptoQuotes().add_handlers(dispatcher)
    Temperatures().add_handlers(dispatcher)

    # Add handler for messages we aren't handling
    dispatcher.add_handler(MessageHandler(Filters.private & (Filters.command | Filters.text), _unknown_handler))


def _unknown_handler(update: Update, context: CallbackContext):
    chat_id = update.effective_user.id
    logger.warning("UNHANDLED MESSAGE {}".format(update.to_dict()))

    context.bot.sendMessage(chat_id=chat_id, text="Did not understand message")
