import abc

from telegram_bot.handlers.decorators import check_allowed_user


class HandlerBase:
    def add_handlers(self, dispatcher):
        # make sure all handlers check that user is allowed
        for klass, kwargs in self._get_handlers():
            callback = kwargs.pop("callback")
            callback = check_allowed_user(callback)
            dispatcher.add_handler(klass(callback=callback, **kwargs))

    @abc.abstractmethod
    def _get_handlers(self):
        """
        returns list of tuples
        :return: list of tuples
        """
