from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler, CallbackQueryHandler


def setup_test_handlers(dispatcher):
    dispatcher.add_handler(CommandHandler('Start', NagiosMenu.start))
    dispatcher.add_handler(CallbackQueryHandler(NagiosMenu.main_menu, pattern='main'))
    dispatcher.add_handler(CallbackQueryHandler(NagiosMenu.first_menu, pattern='m1'))


class NagiosMenu:
    @staticmethod
    def start(update: Update, context: CallbackContext):
        chat_id = update.effective_user.id
        context.bot.sendMessage(chat_id=chat_id,
                                text='Choose the option in main menu:',
                                reply_markup=NagiosKeyboard.main_menu_keyboard())

    @staticmethod
    def first_menu(update, context):
        update.callback_query.message.edit_text('Choose the submenu in first menu:',
                                                reply_markup=NagiosKeyboard.first_menu_keyboard())

    @staticmethod
    def main_menu(update: Update, context: CallbackContext):
        update.callback_query.message.edit_text('Choose the option in main menu:',
                                                reply_markup=NagiosKeyboard.main_menu_keyboard())


class NagiosKeyboard:
    @staticmethod
    def main_menu_keyboard():
        keyboard = [[InlineKeyboardButton('Menu 1', callback_data='m1')],
                    [InlineKeyboardButton('Menu 2', callback_data='m2')],
                    [InlineKeyboardButton('Menu 3', callback_data='m3')]]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def first_menu_keyboard():
        keyboard = [[InlineKeyboardButton('Submenu 1-1', callback_data='m1_1')],
                    [InlineKeyboardButton('Submenu 1-2', callback_data='m1_2')],
                    [InlineKeyboardButton('Main menu', callback_data='main')]]
        return InlineKeyboardMarkup(keyboard)


class NagiosMenuOptionHandler:
    pass
