import requests
import logging
import boto3
import json

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) #TODO: Remove this later on

class GarageDoorHandler:
    def __init__(self, config):
        hostname = config.get('GARAGE', 'hostname')
        port = config.get('GARAGE', 'port')

        user = config.get('GARAGE', 'username')
        password = config.get('GARAGE', 'password')

        self.garage_door_base_url = 'http://{0}:{1}'.format(hostname, port)
        self.garage_door_user_pass = (user, password)

        # Queue where we will listen for responses on
        self.sqs = boto3.resource('sqs')
        self.sns = boto3.client('sns')
        # self._garage_request_arn = '' #TODO: Fill this in via config
        # self._garage_response_queue = sqs.get_queue_by_name(QueueName='garage-responses')



    def _get_garage_position(self, garage_name='all'):
        # Returns whether the garage is open or closed
        # message = {'type': 'STATUS'}
        # response = self.sns.publish_message(TargetArn=self._garage_request_arn,
        #                          Message=json.dumps({'default': json.dumps(message)}),
        #                          Subject='Garage Position Request',
        #                          MessageStructure='json')
        request_url = '{0}/garage/status/{1}'.format(self.garage_door_base_url, garage_name)
        logger.info("Requesting garage status from url".format(request_url))
        r = requests.get(request_url, auth=self.garage_door_user_pass)
        if r.status_code == 200:
            logger.info("Got response as {}".format(r.json()))
            return r.json()

        logger.info("Got response as {}".format(r.json()))
        return []

    def _control_garage(self, garage_name, action):
        request_url = '{0}/garage/control/{1}/{2}'.format(self.garage_door_base_url, garage_name, action)

        r = requests.get(request_url, auth=self.garage_door_user_pass)

        return r

    def status_to_string(self, garage_statuses):
        """
        Parses the garage status dict into a readable string
        :param garage_statuses:
        :return: str
        """
        return_message = ""

        for one_garage_dict in garage_statuses:
            garage_name = one_garage_dict['garage_name']
            current_status = one_garage_dict['status']
            return_message += '{:<5} : {}'.format(garage_name, ' '.join([current_status, one_garage_dict['status_time']])) + '\n'

        return return_message

    def get_keyboard_format(self, garage_statuses):
        """
        returns a list of (key_text, value) from the statuses
        :param garage_statuses:
        :return: str
        """
        options = []
        for one_garage_dict in garage_statuses:
            garage_name = one_garage_dict['garage_name']
            current_status = one_garage_dict['status']

            # Determine whether this can be opened or closed
            if not one_garage_dict['error']:
                action = 'CLOSE' if current_status == 'OPEN' else 'OPEN'
                key_string = ' '.join(['confirm', action, str(garage_name)])
                options.append([key_string])  # Store the key for the keyboard
        options.append(["CANCEL GARAGE"])  # Store the key for the keyboard

        return options

# if __name__ == '__main__':
#     import configparser
#     config = configparser.ConfigParser()
#     config.read('/etc/telegram-bot/bot.config')
#     g = GarageDoorHandler(config)
#     print(g.status_to_string(status_str))
#     # print(g.get_keyboard_format(status_str))
#     pass
