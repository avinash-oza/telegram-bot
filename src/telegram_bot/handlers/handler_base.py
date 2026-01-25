import abc

from telegram_bot.config_helper import ConfigHelper
from telegram_bot.handlers.decorators import check_allowed_user


class HandlerBase:
    def __init__(self, config_helper: ConfigHelper):
        self._config_helper = config_helper

    def add_handlers(self, application):
        # make sure all handlers check that user is allowed
        for klass, kwargs in self._get_handlers():
            # TODO: REVIEW THIS
            # callback = kwargs.pop("callback")
            # callback = check_allowed_user(callback)
            # application.add_handler(klass(callback=callback, **kwargs))
            application.add_handler(klass(**kwargs))

    @abc.abstractmethod
    def _get_handlers(self):
        """
        returns list of tuples
        :return: list of tuples
        """
