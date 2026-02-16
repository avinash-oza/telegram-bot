import datetime
import logging
import re

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

from telegram_bot.config_helper import ConfigHelper
from telegram_bot.handlers.handler_base import HandlerBase

config = ConfigHelper()
logger = logging.getLogger(__name__)

STATE_TYPING_DATE, STATE_CONFIRM_DATE, STATE_TYPING_EVENT, STATE_CONFIRMING = range(4)

EVENT_DATE_INPUT_TEXT = (
    "Please input the date of the event in the following format: YYYY-MM-DD"
)


class GoogleCalendarHandler(HandlerBase):
    def _add_new_event(self, event_date, event_text):
        """

        :param message_text: Handles a message in the following format:
        <Event Name>$<Event Date>
        and adds it to the configured calendar
        """
        logger.info(f"Got event_date={event_date} and event_text={event_text}")
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

        logger.info(f"Completed adding event {event_text} on {event_date} to calendar")

    async def _add_event(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        event_date = context.user_data["formatted_date"]
        event_name = context.user_data["event_name"]

        self._add_new_event(event_date, event_name)

        await update.message.reply_text(
            f"Added event {event_name} on {event_date} to calendar."
        )

        return ConversationHandler.END

    async def _get_event_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(EVENT_DATE_INPUT_TEXT)

        return STATE_TYPING_DATE

    async def _validate_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        try:
            dt = datetime.datetime.strptime(text, "%Y-%m-%d")
        except ValueError:
            await update.message.reply_text(EVENT_DATE_INPUT_TEXT)
            return STATE_TYPING_DATE

        context.user_data["formatted_date"] = dt.strftime("%m/%d/%Y")

        await update.message.reply_text(
            f"Type in the event name",
        )
        return STATE_CONFIRMING

    async def _validate_all_details(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        event_name = update.message.text
        context.user_data["event_name"] = event_name
        event_date = context.user_data["formatted_date"]

        await update.message.reply_text(
            f"Adding event {event_name} on {event_date} to calendar. Type Yes to confirm.",
            reply_markup=ReplyKeyboardMarkup([["Yes"]], one_time_keyboard=True),
        )
        return STATE_CONFIRMING

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
                                filters.Regex("^[0-9]{4}-[0-9]{2}-[0-9]{2}")
                                | filters.Regex(""),
                                self._validate_date,
                            )
                        ],
                        STATE_CONFIRMING: [
                            MessageHandler(
                                filters.Regex("^Yes"),
                                self._add_event,
                            ),
                            MessageHandler(
                                filters.Regex("^.+$"),
                                self._validate_all_details,
                            ),
                        ],
                    },
                    "fallbacks": [],
                },
            )
        ]
