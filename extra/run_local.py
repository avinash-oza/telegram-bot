from telegram.ext import Application

from telegram.ext import DictPersistence
from telegram_bot.config_helper import ConfigHelper
from telegram_bot.webhook import WebHookBuilder

if __name__ == "__main__":
    c = ConfigHelper()
    TELEGRAM_TOKEN = c.get("telegram", "api_key")

    if not TELEGRAM_TOKEN:
        msg = "The TELEGRAM_BOT_API_KEY must be set"
        raise RuntimeError(msg)

    dict_persistence = DictPersistence()
    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .persistence(persistence=dict_persistence)
        .build()
    )

    WebHookBuilder.setup_handlers(application)

    application.run_polling()
