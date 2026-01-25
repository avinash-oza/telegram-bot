import datetime
import logging
import re

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

from telegram_bot.config_helper import ConfigHelper
from telegram_bot.handlers.handler_base import HandlerBase

config = ConfigHelper()
logger = logging.getLogger(__name__)

SUPPORTED_DATE_FORMATS = ["YYYY-MM-DD"]

STATE_TYPING_DATE, STATE_CONFIRM_DATE, STATE_TYPING_EVENT, STATE_CONFIRMING = range(4)


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
        #
        # event_date = arrow.get(event_date, SUPPORTED_DATE_FORMATS)
        # logger.info(f"Parsed {event_title=} and {event_date=}")
        #
        # calendar_config = config.config["calendar"]
        # token = Credentials(
        #     token=calendar_config["token"],
        #     refresh_token=calendar_config["refresh_token"],
        #     client_id=calendar_config["client_id"],
        #     client_secret=calendar_config["client_secret"],
        #     scopes=["https://www.googleapis.com/auth/calendar"],
        #     token_uri="https://oauth2.googleapis.com/token",
        # )
        # cal = GoogleCalendar(
        #     calendar_config["calendar_id"], credentials=token, save_token=False
        # )
        #
        # event = Event(
        #     summary=event_title, start=event_date.date(), end=event_date.date()
        # )
        #
        # cal.add_event(event=event)

        logger.info(f"Completed adding {event_title=} successfully")

    # async def _handle_message(self, update: Update, context: CallbackContext):
    #     quotes_response = self._build_response()
    #
    #     chat_id = update.effective_user.id
    #     await context.bot.sendMessage(
    #         chat_id=chat_id, text=quotes_response, parse_mode="Markdown"
    #     )
    async def _get_event_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # text = update.message.text
        # context.user_data["choice"] = text
        await update.message.reply_text(f"Input the event date in YYYY-MM-DD format")

        return STATE_TYPING_DATE

    async def _validate_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        dt = datetime.datetime.strptime(text, "%Y-%m-%d")
        formatted_date = dt.strftime("%m/%d/%Y")

        await update.message.reply_text(
            f"You input {formatted_date}. Is this correct?",
            reply_markup=ReplyKeyboardMarkup([["Yes"], ["No"]]),
        )

        return ConversationHandler.END

    def _get_handlers(self):
        return [
            (
                ConversationHandler,
                {
                    "entry_points": [
                        MessageHandler(
                            filters.ChatType.PRIVATE
                            & filters.Regex(re.compile("^(calendar)", re.IGNORECASE)),
                            self._get_event_date,
                        )
                    ],
                    "states": {
                        STATE_TYPING_DATE: [
                            MessageHandler(
                                filters.Regex("^[0-9]{4}-[0-9]{2}-[0-9]{2}"),
                                self._validate_date,
                            )
                        ],
                        STATE_TYPING_EVENT: [
                            MessageHandler(
                                filters.Regex("^Yes"),
                                self._validate_date,
                            )
                        ],
                    },
                    "fallbacks": [],
                },
            )
        ]
