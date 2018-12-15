
from telegram.ext import Filters, BaseFilter

class ConfirmFilter(BaseFilter):
    def filter(self, message):
        return message.text.split(' ')[0].lower() == 'confirm'
