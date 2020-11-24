import json
import logging

import arrow
import boto3
from config_util import ConfigHelper
from telegram import InlineKeyboardButton

c = ConfigHelper()
logger = logging.getLogger(__name__)


class GarageDoorHandler:
    def __init__(self):
        self.sqs = boto3.client('sqs')
        self.sns = boto3.client('sns')

    @property
    def _garage_request_arn(self):
        req_arn = c.get('garage', 'request_arn')
        if req_arn is None:
            logger.error("TELEGRAM_GARAGE_REQUEST_ARN is not set, no garage functionality available")
        return req_arn

    @property
    def _garage_response_queue_url(self):
        return self.sqs.get_queue_url(QueueName='garage-responses')['QueueUrl']

    def get_garage_position(self, garage_name='ALL'):
        # Returns whether the garage is open or closed
        message = {'type': 'STATUS', 'garage_name': garage_name}
        return self._send_request_and_parse_sqs_response(message)

    def control_garage(self, garage_name, action):
        message = {'type': 'CONTROL', 'garage_name': garage_name, 'action': action}
        return self._send_request_and_parse_sqs_response(message)

    def _send_request_and_parse_sqs_response(self, message):
        if self._garage_request_arn is None:
            return []  # cannot do anything at this point

        response = self.sns.publish(TargetArn=self._garage_request_arn,
                                    Message=json.dumps({'default': json.dumps(message)}),
                                    Subject='Garage Request',
                                    MessageStructure='json')
        logger.info("Response for request was {}".format(response))
        # To make sure the response goes with the request
        expected_return_id = response['MessageId'][:4]
        logger.info("Sent request for garage status: {}. Waiting for response".format(response))
        logger.info("Expecting return message_id: {}".format(expected_return_id))
        responses = self.sqs.receive_message(QueueUrl=self._garage_response_queue_url, MaxNumberOfMessages=10,
                                             WaitTimeSeconds=3)
        if 'Messages' not in responses:
            logger.error("Did not receive a response about garage status")
            return []
        for response in responses['Messages']:
            garage_statuses = json.loads(response['Body'])
            # check if this was the request we sent
            if garage_statuses['id'] != expected_return_id:
                continue

            logger.info("Received response for the garage as {}".format(garage_statuses))
            # delete message from the queue
            self.sqs.delete_message(QueueUrl=self._garage_response_queue_url, ReceiptHandle=response['ReceiptHandle'])
            return garage_statuses['status']
        logger.error("Did not get any expected responses")
        return []

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
                callback_data = ' '.join(['garage', action, str(garage_name)])
                key_text = '{} the {} Garage'.format(action.capitalize(), garage_name)
                options.append(
                    [InlineKeyboardButton(key_text, callback_data=callback_data)])  # Store the key for the keyboard
        options.append(
            [InlineKeyboardButton("Nevermind", callback_data='garage cancel')])  # Store the key for the keyboard

        return options
