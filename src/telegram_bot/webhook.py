import asyncio
import json
import logging

import telegram
from telegram.ext import Application, MessageHandler, filters

from src.telegram_bot.config_helper import ConfigHelper
from src.telegram_bot.handlers.crypto_quotes_handler import CryptoQuotesHandler
from src.telegram_bot.handlers.garage_door import GarageDoorHandler
from src.telegram_bot.handlers.nagios.menu import setup_nagios_handlers
from src.telegram_bot.handlers.temperature_data import Temperatures
from src.telegram_bot.handlers.unknown_handler import unknown_handler

c = ConfigHelper()

if len(logging.getLogger().handlers) > 0:
    # The Lambda environment pre-configures a handler logging to stderr. If a handler is already configured,
    # `.basicConfig` does not execute. Thus we set the level directly.
    logging.getLogger().setLevel(logging.INFO)
else:
    logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO)

logger = logging.getLogger()

OK_RESPONSE = {
    "statusCode": 200,
    "headers": {"Content-Type": "application/json"},
    "body": json.dumps("ok"),
}
ERROR_RESPONSE = {"statusCode": 400, "body": json.dumps("Oops, something went wrong!")}


def webhook(event, context):
    return WebHookBuilder().run(event, context)


class WebHookBuilder:
    def run(self, event, context):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self._webhook(event, context))

    async def _webhook(self, event, context):
        """
        Runs the Telegram webhook.
        """

        application = self._create_application()

        self.setup_handlers(application)

        logger.info("Event: {}".format(event))

        if event.get("httpMethod") == "POST" and event.get("body"):
            logger.info("Processing received message")
            update = telegram.Update.de_json(
                json.loads(event.get("body")), application.bot
            )
            chat_id = update.effective_user
            text = update.effective_message

            async with application:
                await application.process_update(update)

            logger.info(f"chat_id={chat_id}, TEXT:{text}")
            logger.info("Message sent")

        elif event.get("httpMethod") == "GET" and event.get("path") == "/setWebHook":
            logger.info("Setting webhook")
            self._set_webhook(event, context, application.bot)

        return OK_RESPONSE

    @staticmethod
    def _create_application():
        """
        Configures the bot with a Telegram Token.

        Returns a bot instance.
        """

        TELEGRAM_TOKEN = c.get("telegram", "api_key")
        if not TELEGRAM_TOKEN:
            msg = "The TELEGRAM_BOT_API_KEY must be set"
            logger.error(msg)
            raise RuntimeError(msg)

        application = Application.builder().token(TELEGRAM_TOKEN).build()

        return application

    @staticmethod
    def _set_webhook(event, context, bot):
        """
        Sets the Telegram bot webhook.
        """

        logger.info("Got request to set webhook")
        logger.info(f"EVENT: {event}")

        url = f"https://{event.get('headers').get('Host')}/"

        logger.info(f"Setting webhook url={url}")
        webhook = bot.set_webhook(url)

        if webhook:
            logger.info(f"Successfully set webhook")
            return OK_RESPONSE

        return ERROR_RESPONSE

    @staticmethod
    def setup_handlers(application):
        GarageDoorHandler().add_handlers(application)
        CryptoQuotesHandler().add_handlers(application)
        Temperatures().add_handlers(application)
        setup_nagios_handlers(application)

        # Add handler for messages we aren't handling
        application.add_handler(
            MessageHandler(
                filters.ChatType.PRIVATE,
                unknown_handler,
            )
        )
