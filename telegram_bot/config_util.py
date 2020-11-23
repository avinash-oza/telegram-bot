import boto3

import logging
import json

logger = logging.getLogger(__name__)

class ConfigHelper:
    def __init__(self, env_name):
        self._db = boto3.client('dynamodb')
        self._env_name = env_name.lower()

    def get_config(self):
        results = self._db.query(TableName='configTable',
                KeyConditionExpression="lookup_key = :k_name",
                ExpressionAttributeValues={
                    ':k_name': {'S': 'telegram-bot+dev'}
                    })
        if len(results['Items']) != 1:
            raise ValueError("Got multiple configs for key")
        config_str = results['Items'][0]['value']['S']
        config = json.loads(config_str)

        return config

if __name__== '__main__':
    c = ConfigHelper('dev')
    print(c.get_config()['key1'])
