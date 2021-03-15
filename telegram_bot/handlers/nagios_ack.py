from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler, CallbackQueryHandler


def setup_test_handlers(dispatcher):
    dispatcher.add_handler(CommandHandler('Start', start))
    dispatcher.add_handler(CallbackQueryHandler(main_menu, pattern='main'))
    dispatcher.add_handler(CallbackQueryHandler(first_menu, pattern='m1'))


def start(update: Update, context: CallbackContext):
    chat_id = update.effective_user.id
    context.bot.sendMessage(chat_id=chat_id, text=main_menu_message(),
                            reply_markup=main_menu_keyboard())


def main_menu_message():
    return 'Choose the option in main menu:'


def main_menu_keyboard():
    keyboard = [[InlineKeyboardButton('Menu 1', callback_data='m1')],
                [InlineKeyboardButton('Menu 2', callback_data='m2')],
                [InlineKeyboardButton('Menu 3', callback_data='m3')]]
    return InlineKeyboardMarkup(keyboard)


def main_menu(update: Update, context: CallbackContext):
    update.callback_query.message.edit_text(main_menu_message(),
                                            reply_markup=main_menu_keyboard())


def first_menu(update, context):
    update.callback_query.message.edit_text(first_menu_message(),
                                            reply_markup=first_menu_keyboard())


def first_menu_keyboard():
    keyboard = [[InlineKeyboardButton('Submenu 1-1', callback_data='m1_1')],
                [InlineKeyboardButton('Submenu 1-2', callback_data='m1_2')],
                [InlineKeyboardButton('Main menu', callback_data='main')]]
    return InlineKeyboardMarkup(keyboard)


def first_menu_message():
    return 'Choose the submenu in first menu:'
