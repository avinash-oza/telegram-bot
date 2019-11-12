import json
import telegram
import os
import logging


# Logging is cool!
from telegram.ext import Dispatcher

from telegram_bot.start_telegram_bot import setup_handlers

logger = logging.getLogger()
if logger.handlers:
    for handler in logger.handlers:
        logger.removeHandler(handler)
logging.basicConfig(level=logging.INFO)

OK_RESPONSE = {
    'statusCode': 200,
    'headers': {'Content-Type': 'application/json'},
    'body': json.dumps('ok')
}
ERROR_RESPONSE = {
    'statusCode': 400,
    'body': json.dumps('Oops, something went wrong!')
}


def configure_telegram():
    """
    Configures the bot with a Telegram Token.

    Returns a bot instance.
    """

    TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_API_KEY')
    if not TELEGRAM_TOKEN:
        logger.error('The TELEGRAM_TOKEN must be set')
        raise NotImplementedError

    bot = telegram.Bot(TELEGRAM_TOKEN)

    return bot


def webhook(event, context):
    """
    Runs the Telegram webhook.
    """

    bot = configure_telegram()
    dispatcher = Dispatcher(bot, None, workers=0)

    setup_handlers(dispatcher)

    logger.info('Event: {}'.format(event))

    if event.get('httpMethod') == 'POST' and event.get('body'):
        logger.info('Message received')
        update = telegram.Update.de_json(json.loads(event.get('body')), bot)
        chat_id = update.message.chat.id
        text = update.message.text

        dispatcher.process_update(update)

        logger.info(f"chat_id={chat_id}, TEXT:{text}")
        logger.info('Message sent')

        return OK_RESPONSE

    return ERROR_RESPONSE


def set_webhook(event, context):
    """
    Sets the Telegram bot webhook.
    """

    logger.info('Event: {}'.format(event))
    bot = configure_telegram()
    url = 'https://{}/{}/'.format(
        event.get('headers').get('Host'),
        event.get('requestContext').get('stage'),
    )
    webhook = bot.set_webhook(url)

    if webhook:
        return OK_RESPONSE

    return ERROR_RESPONSE



if __name__ == '__main__':
    user_id = os.environ.get('TELEGRAM_USER', 1234)  # sample id for testing

    msg_body = {'update_id': 57665158, 'message': {'message_id': 458,
                                                   'from': {'id': user_id, 'is_bot': False, 'first_name': 'ABCD',
                                                            'language_code': 'en'},
                                                   'chat': {'id': user_id, 'first_name': 'ABCD', 'type': 'private'},
                                                   'date': 1573350422, 'text': '/quotes'}}
    d = {'resource': '/', 'path': '/', 'httpMethod': 'POST',
         'requestContext': {'httpMethod': 'POST',
                            'requestTime': '10/Nov/2019:01:51:04 +0000'},
         'body': json.dumps(msg_body),
         'isBase64Encoded': False}

    webhook(d, {})
