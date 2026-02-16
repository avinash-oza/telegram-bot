import datetime
import logging
import re
import tempfile

import boto3
from gcsa.event import Event
from gcsa.google_calendar import GoogleCalendar
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
    def _add_new_event(self, event_date: str, event_text: str):
        """

        :param message_text: Handles a message in the following format:
        <Event Name>$<Event Date>
        and adds it to the configured calendar
        """
        logger.info(f"Got event_date={event_date} and event_text={event_text}")

        event_date_obj = datetime.datetime.strptime(event_date, "%m/%d/%Y")

        calendar_config = config.config["calendar"]
        calendar_id = calendar_config["calendar_id"]
        bucket_name = calendar_config["credentials_bucket_name"]
        bucket_path_token = calendar_config["credentials_token_path"]
        bucket_path_credentials = calendar_config["credentials_path"]

        with tempfile.TemporaryDirectory() as temp_dir:
            s3_client = boto3.client("s3")
            # download to temp dir
            token_path = f"{temp_dir}/token.pickle"
            s3_client.download_file(bucket_name, bucket_path_token, token_path)

            credentials_path = f"{temp_dir}/credentials.json"
            s3_client.download_file(
                bucket_name, bucket_path_credentials, credentials_path
            )

            cal = GoogleCalendar(
                calendar_id,
                token_path=token_path,
                credentials_path=credentials_path,
            )

            logger.info("Uploading refreshed token to S3")
            s3_client.upload_file(token_path, bucket_name, bucket_path_token)

        event = Event(
            summary=event_text, start=event_date_obj.date(), end=event_date_obj.date()
        )

        cal.add_event(event=event)

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
        event_name = update.message.text.upper()
        context.user_data["event_name"] = event_name
        event_date = context.user_data["formatted_date"]

        await update.message.reply_text(
            f"Adding event {event_name} on {event_date} to calendar. Select Yes to confirm, No to change the date"
            f" or type to change event details.",
            reply_markup=ReplyKeyboardMarkup([["Yes"], ["No"]], one_time_keyboard=True),
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
                                filters.Regex("^No"),
                                self._validate_date,
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


if __name__ == "__main__":
    # for testing
    handler = GoogleCalendarHandler(ConfigHelper())
    handler._add_new_event("2024-06-30", "Test Event")
