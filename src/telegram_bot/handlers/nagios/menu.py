import datetime
import logging
import re

import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, CallbackQueryHandler, MessageHandler, filters

from telegram_bot.config_helper import ConfigHelper

logger = logging.getLogger(__name__)
config = ConfigHelper()

SUPPORTED_COMMANDS = {
    "SCHEDULE_SVC_DOWNTIME": "SCHEDULE_SVC_DOWNTIME;{host_name};{service_name};{start_time};{end_time};1;0;{time_window};{author};{comment}"
}

TIME_WINDOW_DAYS = 1


def setup_nagios_handlers(dispatcher):
    start_handler = MessageHandler(
        filters=filters.ChatType.PRIVATE
        & filters.Regex(re.compile("^(Na)", re.IGNORECASE)),
        callback=NagiosMenu.start,
    )
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(
        CallbackQueryHandler(NagiosMenu.server_menu, pattern="server")
    )
    dispatcher.add_handler(
        CallbackQueryHandler(NagiosMenu.service_menu, pattern="service")
    )
    dispatcher.add_handler(
        CallbackQueryHandler(NagiosMenu.action_menu, pattern="action")
    )
    dispatcher.add_handler(
        CallbackQueryHandler(NagiosMenuOptionHandler.execute_command, pattern="execute")
    )


class NagiosMenu:
    @staticmethod
    async def start(update: Update, context: CallbackContext):
        chat_id = update.effective_user.id
        await context.bot.sendMessage(
            chat_id=chat_id,
            text="Choose a server:",
            reply_markup=NagiosKeyboard.server_keyboard(),
        )

    @staticmethod
    async def service_menu(update, context: CallbackContext):
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            "Choose a service on the Server:",
            reply_markup=NagiosKeyboard.service_keyboard(update.callback_query.data),
        )

    @staticmethod
    async def server_menu(update: Update, context: CallbackContext):
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            "Choose a server:", reply_markup=NagiosKeyboard.server_keyboard()
        )

    @staticmethod
    async def action_menu(update: Update, context: CallbackContext):
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            "Choose an action to run:",
            reply_markup=NagiosKeyboard.action_keyboard(update.callback_query.data),
        )


class NagiosKeyboard:
    @staticmethod
    def server_keyboard():
        servers = config.config["nagios"]["servers"]
        return build_keyboard_from_options(servers, "", "service", add_main_menu=False)

    @staticmethod
    def service_keyboard(chat_data):
        services = config.config["nagios"]["services"]
        return build_keyboard_from_options(services, chat_data, "action")

    @staticmethod
    def action_keyboard(chat_data):
        actions = config.config["nagios"]["actions"]
        return build_keyboard_from_options(actions, chat_data, "execute")


class NagiosMenuOptionHandler:
    @staticmethod
    async def execute_command(update, context: CallbackContext):
        await update.callback_query.answer()
        logger.info(f"Got command string: {update.callback_query.data}")
        msg = convert_callback_data(update.callback_query.data)

        await update.callback_query.message.edit_text(msg)


def build_keyboard_from_options(
    options, prior_callback_data, callback_prefix, add_main_menu=True
):
    keyboard = []
    for idx, action in enumerate(options):
        keyboard.append(
            [
                InlineKeyboardButton(
                    action["name"],
                    callback_data=f"{callback_prefix}|{prior_callback_data}|{idx}",
                )
            ]
        )

    if add_main_menu:
        keyboard.append([InlineKeyboardButton("Main Menu", callback_data="server")])
    return InlineKeyboardMarkup(keyboard)


def convert_callback_data(callback_str):
    # example is execute|action|service|1|0|0
    text_options = []
    for option, option_list in zip(
        callback_str[::-1].split("|"), ["actions", "services", "servers"]
    ):
        text_options.append(
            key_to_callback_data(int(option), config.config["nagios"][option_list])
        )

    command, service, host = text_options
    logger.info(
        f"Selected option list: command={command}, service={service}, host={host}"
    )
    return submit_command(command, service, host)


def key_to_callback_data(key, options):
    d = {idx: option["callback"] for idx, option in enumerate(options)}
    return d[key]


def submit_command(command_name, service, host):
    command_name = command_name.upper()
    try:
        cmd_str = SUPPORTED_COMMANDS[command_name]
    except KeyError:
        return f"Received an unsupported command: {command_name}"

    start_time = datetime.datetime.today()
    end_time = start_time + datetime.timedelta(days=TIME_WINDOW_DAYS)

    formatted_str = cmd_str.format(
        host_name=host,
        service_name=service,
        start_time=round(start_time.timestamp()),
        end_time=round(end_time.timestamp()),
        time_window=TIME_WINDOW_DAYS * 60 * 60 * 24,
        author="telegram-bot",
        comment="Added by telegram-bot",
    )
    payload = {
        "token": config.config["nagios"]["passive_checks"]["api_key"],
        "cmd": "submitcmd",
        "command": formatted_str,
    }
    resp = requests.post(
        config.config["nagios"]["passive_checks"]["endpoint"], params=payload
    )

    try:
        resp.raise_for_status()
    except Exception as e:
        logger.exception("Error when trying to run command")
        return f"Exception when running command: {str(e)}"
    else:
        return f"Successfully ran command: {command_name}"
