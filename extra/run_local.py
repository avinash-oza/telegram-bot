from telegram.ext import Application, DictPersistence

from telegram_bot.config_helper import ConfigHelper
from telegram_bot.webhook import WebHookBuilder

if __name__ == "__main__":
    config_helper = ConfigHelper()
    TELEGRAM_TOKEN = config_helper.get("telegram", "api_key")

    if not TELEGRAM_TOKEN:
        msg = "The TELEGRAM_BOT_API_KEY must be set"
        raise RuntimeError(msg)

    my_persistence = DictPersistence()
    application = (
        Application.builder()
        .persistence(persistence=my_persistence)
        .token(TELEGRAM_TOKEN)
        .build()
    )

    WebHookBuilder(config_helper).setup_handlers(application)
    # For setting the webhook in asyncmode
    # asyncio.run(WebHookBuilder._set_webhook({}, {}, application.bot))

    application.run_polling()
