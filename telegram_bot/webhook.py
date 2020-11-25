import json
import logging

import telegram
from telegram_bot.config_util import ConfigHelper
from telegram.ext import Dispatcher

from telegram_bot.handlers import setup_handlers

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


def configure_telegram():
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
        chat_id = update.effective_user
        text = update.effective_message

        dispatcher.process_update(update)

        logger.info(f"chat_id={chat_id}, TEXT:{text}")
        logger.info('Message sent')

    elif event.get('httpMethod') == 'GET' and event.get('path') == '/setWebHook':
        logger.info("Setting webhook")
        set_webhook(event, context)

    return OK_RESPONSE


def set_webhook(event, context):
    """
    Sets the Telegram bot webhook.
    """

    logger.info('Got request to set webhook')
    logger.info(f'EVENT: {event}')

    bot = configure_telegram()
    url = f"https://{event.get('headers').get('Host')}/"

    logger.info(f'Setting webhook url={url}')
    webhook = bot.set_webhook(url)

    if webhook:
        logger.info(f'Successfully set webhook')
        return OK_RESPONSE

    return ERROR_RESPONSE

if __name__ == '__main__':
    import os
    user_id = os.environ.get('TELEGRAM_USER', 1234)  # sample id for testing

    # standard sample message
    msg_body = {'update_id': 57665158, 'message': {'message_id': 458,
                                                   'from': {'id': user_id, 'is_bot': False, 'first_name': 'ABCD',
                                                            'language_code': 'en'},
                                                   'chat': {'id': user_id, 'first_name': 'ABCD', 'type': 'private'},
                                                   'date': 1573350422, 'text': 'quotes'}}
    # sample callback message
    # msg_body = {'update_id': 57665158,
    #             'message': {'message_id': 458,
    #                         'from': {'id': user_id, 'is_bot': False, 'first_name': 'ABCD',
    #                                  'language_code': 'en'},
    #                         'chat': {'id': user_id, 'first_name': 'ABCD', 'type': 'private'},
    #                         'date': 1573350422, 'text': 'Ga'},
    #
    #             'callback_query': {'id': user_id,
    #                                'from_user': user_id,
    #                                'chat_instance': '34567',
    #                                'data': 'garage cancel'
    #                                }
    #             }

    d = {'resource': '/', 'path': '/', 'httpMethod': 'POST',
         'requestContext': {'httpMethod': 'POST',
                            'requestTime': '10/Nov/2019:01:51:04 +0000'},
         'body': json.dumps(msg_body),
         'isBase64Encoded': False}

    webhook(d, {})
