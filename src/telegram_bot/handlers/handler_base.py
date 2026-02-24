import abc

from telegram.ext import ConversationHandler

from telegram_bot.config_helper import ConfigHelper
from telegram_bot.handlers.decorators import check_allowed_user


class HandlerBase:
    def __init__(self, config_helper: ConfigHelper):
        self._config_helper = config_helper

    def add_handlers(self, application):
        # make sure all handlers check that user is allowed
        for klass, kwargs in self._get_handlers():
            if klass is not ConversationHandler:
                callback = kwargs.pop("callback")
                callback = check_allowed_user(callback)
                application.add_handler(klass(callback=callback, **kwargs))
                continue

            # ConversationHandlers are a special case since they have multiple callbacks (entry points, states, fallbacks)
            # Wrap all callbacks in the conversation states
            if "states" in kwargs:
                for state_key, handlers_list in kwargs["states"].items():
                    for handler in handlers_list:
                        if hasattr(handler, "callback"):
                            handler.callback = check_allowed_user(handler.callback)

            # Wrap entry point callbacks
            if "entry_points" in kwargs:
                for handler in kwargs["entry_points"]:
                    if hasattr(handler, "callback"):
                        handler.callback = check_allowed_user(handler.callback)

            # Wrap fallback callbacks
            if "fallbacks" in kwargs:
                for handler in kwargs["fallbacks"]:
                    if hasattr(handler, "callback"):
                        handler.callback = check_allowed_user(handler.callback)

            application.add_handler(klass(**kwargs))

    @abc.abstractmethod
    def _get_handlers(self):
        """
        returns list of tuples
        :return: list of tuples
        """
