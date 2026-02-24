from telegram.ext import Application

from telegram_bot.config_helper import ConfigHelper
from telegram_bot.webhook import WebHookBuilder

if __name__ == "__main__":
    c = ConfigHelper()
    TELEGRAM_TOKEN = c.get("telegram", "api_key")

    if not TELEGRAM_TOKEN:
        msg = "The TELEGRAM_BOT_API_KEY must be set"
        raise RuntimeError(msg)

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    WebHookBuilder.setup_handlers(application)
    # For setting the webhook in asyncmode
    # asyncio.run(WebHookBuilder._set_webhook({}, {}, application.bot))

    application.run_polling()
