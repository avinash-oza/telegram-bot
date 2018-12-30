import requests
import logging
import boto3
import json
import datetime

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
        self.sqs = boto3.client('sqs')
        self.sns = boto3.client('sns')
        self._garage_request_arn = config.get('GARAGE', 'request_arn')
        self._garage_response_queue_url = self.sqs.get_queue_url(QueueName='garage-responses')['QueueUrl']


    def _get_garage_position(self, garage_name='ALL'):
        # Returns whether the garage is open or closed
        message = {'type': 'STATUS', 'garage_name': garage_name}
        response = self.sns.publish(TargetArn=self._garage_request_arn,
                                 Message=json.dumps({'default': json.dumps(message)}),
                                 Subject='Garage Position Request',
                                 MessageStructure='json')
        logger.info("Response for request was {}".format(response))
        # To make sure the response goes with the request
        expected_return_id = response['MessageId'][:4]

        logger.info("Sent request for garage status: {}. Waiting for response".format(response))
        logger.info("Expecting return message_id: {}".format(expected_return_id))

        responses = self.sqs.receive_message(QueueUrl=self._garage_response_queue_url, MaxNumberOfMessages=10, WaitTimeSeconds=10)

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
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')

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
