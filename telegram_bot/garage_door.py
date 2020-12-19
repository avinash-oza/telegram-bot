import logging

import arrow
import requests
from telegram import InlineKeyboardButton

from telegram_bot.config_util import ConfigHelper

c = ConfigHelper()
logger = logging.getLogger(__name__)

GARAGE_CALLBACK_PATTERN = '!garage'


class GarageDoorHandler:
    def __init__(self):
        self._garage_config = c.config['garage']

    def get_garage_position(self):
        # Returns whether the garage is open or closed
        url = self._garage_config[f'status_endpoint']
        session = self._get_session()
        resp = session.get(url)
        resp.raise_for_status()

        return resp.json()['status']

    def control_garage(self, garage_name, action):
        message = {'action': action, 'type': 'CONTROL'}
        url = self._garage_config[f'control_endpoint'] + f'/{garage_name.upper()}'
        session = self._get_session()
        resp = session.post(url, json=message)
        resp.raise_for_status()

        return resp.json()['status']

    def _get_session(self):
        username = self._garage_config['username']
        password = self._garage_config['password']
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
        current_time = arrow.now().strftime('%Y-%m-%d %I:%M:%S %p')

        for one_garage_dict in garage_statuses:
            garage_name = one_garage_dict['garage_name']
            current_status = one_garage_dict['status']
            return_message += '{:<5} : {}'.format(garage_name, ' '.join([current_status, current_time])) + '\n'

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
            garage_name = one_garage_dict['garage_name']
            current_status = one_garage_dict['status']

            # Determine whether this can be opened or closed
            if not one_garage_dict['error']:
                action = 'CLOSE' if current_status == 'OPEN' else 'OPEN'
                callback_data = ' '.join([GARAGE_CALLBACK_PATTERN, action, str(garage_name)])
                key_text = '{} the {} Garage'.format(action.capitalize(), garage_name)
                options.append(
                    [InlineKeyboardButton(key_text, callback_data=callback_data)])  # Store the key for the keyboard
        options.append(
            [InlineKeyboardButton("Nevermind",
                                  callback_data=f'{GARAGE_CALLBACK_PATTERN} cancel')])  # Store the key for the keyboard

        return options
