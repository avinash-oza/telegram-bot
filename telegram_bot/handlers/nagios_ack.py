import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler, CallbackQueryHandler

from config_util import ConfigHelper

logger = logging.getLogger(__name__)
config = ConfigHelper()


def setup_test_handlers(dispatcher):
    dispatcher.add_handler(CommandHandler('Start', NagiosMenu.start))
    dispatcher.add_handler(CallbackQueryHandler(NagiosMenu.server_menu, pattern='server'))
    dispatcher.add_handler(CallbackQueryHandler(NagiosMenu.service_menu, pattern='service'))
    dispatcher.add_handler(CallbackQueryHandler(NagiosMenu.action_menu, pattern='action'))
    dispatcher.add_handler(CallbackQueryHandler(NagiosMenuOptionHandler.execute_command, pattern='execute'))


class NagiosMenu:
    @staticmethod
    def start(update: Update, context: CallbackContext):
        chat_id = update.effective_user.id
        context.bot.sendMessage(chat_id=chat_id,
                                text='Choose a server:',
                                reply_markup=NagiosKeyboard.server_keyboard())

    @staticmethod
    def service_menu(update, context: CallbackContext):
        update.callback_query.message.edit_text('Choose a service on the Server:',
                                                reply_markup=NagiosKeyboard.service_keyboard(
                                                    update.callback_query.data))

    @staticmethod
    def server_menu(update: Update, context: CallbackContext):
        update.callback_query.message.edit_text('Choose a server:',
                                                reply_markup=NagiosKeyboard.server_keyboard())

    @staticmethod
    def action_menu(update: Update, context: CallbackContext):
        update.callback_query.message.edit_text('Choose an action to run:',
                                                reply_markup=NagiosKeyboard.action_keyboard(update.callback_query.data))


class NagiosKeyboard:
    @staticmethod
    def server_keyboard():
        servers = config.config['nagios']['servers']
        return build_keyboard_from_options(servers, '', 'service')

    @staticmethod
    def service_keyboard(chat_data):
        services = config.config['nagios']['services']
        return build_keyboard_from_options(services, chat_data, 'action')

    @staticmethod
    def action_keyboard(chat_data):
        actions = config.config['nagios']['actions']
        return build_keyboard_from_options(actions, chat_data, 'execute')


class NagiosMenuOptionHandler:
    @staticmethod
    def execute_command(update, context: CallbackContext):
        update.callback_query.answer()
        logger.info(f"Got command string: {update.callback_query.data}")
        convert_callback_data(update.callback_query.data)
        msg = "Successfully ran command"
        update.callback_query.message.edit_text(msg)


def build_keyboard_from_options(options, prior_callback_data, callback_prefix):
    keyboard = []
    for idx, action in enumerate(options):
        keyboard.append(
            [InlineKeyboardButton(action['name'], callback_data=f"{callback_prefix}|{prior_callback_data}|{idx}")]
        )

    keyboard.append([InlineKeyboardButton('Main Menu', callback_data='server')])
    return InlineKeyboardMarkup(keyboard)


def convert_callback_data(callback_str):
    # example is execute|action|service|1|0|0
    text_options = []
    for option, option_list in zip(callback_str[::-1].split('|'),
                                   ['actions', 'services', 'servers']):
        text_options.append(key_to_callback_data(int(option), config.config['nagios'][option_list]))

    logger.info(f"Selected option list: {text_options}")


def key_to_callback_data(key, options):
    d = {idx: option['callback'] for idx, option in enumerate(options)}
    return d[key]
