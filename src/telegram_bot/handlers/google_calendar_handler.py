import logging
import re

import arrow
from gcsa.event import Event
from gcsa.google_calendar import GoogleCalendar
from google.oauth2.credentials import Credentials
from telegram import Update
from telegram.ext import CallbackContext, MessageHandler, filters

from telegram_bot.config_helper import ConfigHelper
from telegram_bot.handlers.handler_base import HandlerBase

config = ConfigHelper()
logger = logging.getLogger(__name__)

SUPPORTED_DATE_FORMATS = ["YYYY-MM-DD"]


class GoogleCalendarHandler(HandlerBase):
    def add_new_event(self, message_text):
        """

        :param message_text: Handles a message in the following format:
        <Event Name>$<Event Date>
        and adds it to the configured calendar
        """
        message_parts = message_text.split("$", maxsplit=2)
        message_parts = [s.strip() for s in message_parts]

        logger.info(f"Got {message_parts=}")
        event_title, event_date = message_parts

        event_date = arrow.get(event_date, SUPPORTED_DATE_FORMATS)
        logger.info(f"Parsed {event_title=} and {event_date=}")

        calendar_config = config.config["calendar"]
        token = Credentials(
            token=calendar_config["token"],
            refresh_token=calendar_config["refresh_token"],
            client_id=calendar_config["client_id"],
            client_secret=calendar_config["client_secret"],
            scopes=["https://www.googleapis.com/auth/calendar"],
            token_uri="https://oauth2.googleapis.com/token",
        )
        cal = GoogleCalendar(
            calendar_config["calendar_id"], credentials=token, save_token=False
        )

        event = Event(
            summary=event_title, start=event_date.date(), end=event_date.date()
        )

        cal.add_event(event=event)

        logger.info(f"Completed adding {event_title=} successfully")

    async def _handle_message(self, update: Update, context: CallbackContext):
        quotes_response = self._build_response()

        chat_id = update.effective_user.id
        await context.bot.sendMessage(
            chat_id=chat_id, text=quotes_response, parse_mode="Markdown"
        )

    def _get_handlers(self):
        return [
            (
                MessageHandler,
                {
                    "filters": filters.ChatType.PRIVATE
                    & filters.Regex(re.compile("^(quotes)", re.IGNORECASE)),
                    "callback": self._handle_message,
                },
            )
        ]


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s"
    )

    GoogleCalendarHandler().add_new_event("""My name$2024-01-02""")
