import logging
import re

import arrow
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import Update
from telegram.ext import CallbackContext, MessageHandler, filters, CallbackQueryHandler

from telegram_bot.config_helper import ConfigHelper
from telegram_bot.handlers.handler_base import HandlerBase

c = ConfigHelper()
logger = logging.getLogger(__name__)


class GarageDoorHandler(HandlerBase):
    def __init__(self):
        self._garage_config = c.config["garage"]

    def get_garage_position(self):
        # Returns whether the garage is open or closed
        url = self._garage_config[f"status_endpoint"]
        session = self._get_session()
        resp = session.get(url, timeout=self._garage_config["timeout"])
        resp.raise_for_status()

        return resp.json()["status"]

    def control_garage(self, garage_name, action):
        message = {"action": action, "type": "CONTROL"}
        url = self._garage_config[f"control_endpoint"] + f"/{garage_name.upper()}"
        session = self._get_session()
        resp = session.post(url, json=message, timeout=self._garage_config["timeout"])
        resp.raise_for_status()

        return resp.json()["status"]

    def _get_session(self):
        username = self._garage_config["username"]
        password = self._garage_config["password"]
        session = requests.Session()
        session.auth = (username, password)

        return session

    def status_to_string(self, garage_statuses):
        """
        Parses the garage status dict into a readable string
        :param garage_statuses:
        :return: str
        """
        return_message = ""
        current_time = arrow.now().strftime("%Y-%m-%d %I:%M:%S %p")

        for one_garage_dict in garage_statuses:
            garage_name = one_garage_dict["garage_name"]
            current_status = one_garage_dict["status"]
            return_message += (
                "{:<5} : {}".format(
                    garage_name, " ".join([current_status, current_time])
                )
                + "\n"
            )

        return return_message

    def get_keyboard_format(self, garage_statuses):
        """
        returns a list of (key_text, value) from the statuses
        :param garage_statuses:
        :return: str
        """
        if not garage_statuses:
            return []

        options = []
        for one_garage_dict in garage_statuses:
            garage_name = one_garage_dict["garage_name"]
            current_status = one_garage_dict["status"]

            # Determine whether this can be opened or closed
            if not one_garage_dict["error"]:
                action = "CLOSE" if current_status == "OPEN" else "OPEN"
                callback_data = " ".join(["garage", action, str(garage_name)])
                key_text = "{} the {} Garage".format(action.capitalize(), garage_name)
                options.append(
                    [InlineKeyboardButton(key_text, callback_data=callback_data)]
                )  # Store the key for the keyboard
        options.append(
            [InlineKeyboardButton("Nevermind", callback_data="garage cancel")]
        )  # Store the key for the keyboard

        return options

    def _get_handlers(self):
        return [
            (
                MessageHandler,
                {
                    "filters": filters.ChatType.PRIVATE
                    & (
                        filters.Regex(re.compile("^(Garage)", re.IGNORECASE))
                        | filters.Regex(re.compile("^(Ga)", re.IGNORECASE))
                    ),
                    "callback": self.garage_actions_handler,
                },
            ),
            (
                CallbackQueryHandler,
                {"pattern": "^garage", "callback": self.garage_actions_handler},
            ),
        ]

    async def garage_actions_handler(self, update: Update, context: CallbackContext):
        garage_handler = self

        return_message = """"""
        sender_id = update.effective_user.id
        # Gives menu to select which garage to open
        if update.callback_query is None:
            logger.info("Got request to open garage from {}".format(sender_id))

            garage_statuses = garage_handler.get_garage_position()
            if not garage_statuses:
                await context.bot.sendMessage(
                    chat_id=sender_id,
                    text="An exception occurred while getting garage status",
                    reply_keyboard=None,
                )
                return
            # Create the response message
            return_message += "Pick a garage:\n"
            return_message += garage_handler.status_to_string(garage_statuses)

            # create the keyboard
            keyboard_options = garage_handler.get_keyboard_format(garage_statuses)
            reply_keyboard = InlineKeyboardMarkup(
                keyboard_options, one_time_keyboard=True
            )
            await context.bot.sendMessage(
                chat_id=sender_id, text=return_message, reply_markup=reply_keyboard
            )

            return

        if update.callback_query is not None:
            await update.callback_query.answer()
            action_and_garage = update.callback_query.data
            if action_and_garage == "garage cancel":
                logger.info("Cancelled request to open garage")
                await update.callback_query.edit_message_text("Not doing anything")
                return

            # process a confirm action
            action, garage = action_and_garage.lstrip("garage ").split(" ")
            logger.warning(
                "Got confirmation for triggering garage: {} and action: {}".format(
                    garage, action
                )
            )

            await update.callback_query.edit_message_text(
                "Triggering the {} garage to {}".format(
                    garage.capitalize(), action.lower()
                )
            )

            bot_admin = c.config["telegram"]["bot_admin"]
            if update.effective_user.id != bot_admin:
                await context.bot.sendMessage(
                    chat_id=bot_admin,
                    text=f"{update.effective_user.first_name} has action={action} the garage",
                )

            r = garage_handler.control_garage(garage, action)

            if not r:
                await update.callback_query.edit_message_text(
                    "An error occurred while trying to trigger the garage."
                )
                return

            # check for any errors in triggering
            if any([resp["error"] for resp in r]):
                # join the errors together
                await update.callback_query.edit_message_text(
                    "|".join(resp["message"] for resp in r)
                )
                return

            # No errors

            logger.info(
                "User triggered opening of garage sender_id={} garage_name={}".format(
                    sender_id, garage
                )
            )

            await update.callback_query.edit_message_text(
                "Triggered garage, check status separately"
            )
            #
            return
