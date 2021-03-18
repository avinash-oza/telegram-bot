from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler, CallbackQueryHandler

import logging

logger = logging.getLogger(__name__)


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
        servers = ['s1', 's2', 's3']
        keyboard = []
        #             [InlineKeyboardButton('Menu 3', callback_data='m3')]]
        for server in servers:
            keyboard.append(
                [InlineKeyboardButton(server, callback_data=f'service|{server}')]
            )
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def service_keyboard(chat_data):
        services = ['service_1', 'service_2', 'service_3']
        keyboard = []
        #             [InlineKeyboardButton('Main menu', callback_data='main')]]
        for service in services:
            keyboard.append(
                [InlineKeyboardButton(service, callback_data=f'action|{chat_data}|{service}')]
            )
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def action_keyboard(chat_data):
        actions = ['Schedule_Downtime', 'Acknowledge']
        keyboard = []
        #             [InlineKeyboardButton('Main menu', callback_data='main')]]
        for action in actions:
            keyboard.append(
                [InlineKeyboardButton(action, callback_data=f'execute|{chat_data}|{action}')]
            )
        return InlineKeyboardMarkup(keyboard)


class NagiosMenuOptionHandler:
    @staticmethod
    def execute_command(update, context: CallbackContext):
        update.callback_query.answer()
        logger.info(f"Got command string: {update.callback_query.data}")

        msg = "Successfully ran command"
        update.callback_query.message.edit_text(msg)
