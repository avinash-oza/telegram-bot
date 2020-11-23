import boto3

import logging
import json

logger = logging.getLogger(__name__)

class ConfigHelper:
    def __init__(self, env_name):
        self._db = boto3.client('dynamodb')
        self._env_name = env_name.lower()
        self.__config = None

    def get(self, section, value):
        return self.config[section][value]

    @property
    def config(self):
        if self.__config is None:
            results = self._db.query(TableName='configTable',
                    KeyConditionExpression="lookup_key = :k_name",
                    ExpressionAttributeValues={
                        ':k_name': {'S': f'telegram-bot+{self._env_name}'}
                        })
            if len(results['Items']) != 1:
                raise ValueError("Got multiple configs for key")
            config_str = results['Items'][0]['value']['S']
            self.__config = json.loads(config_str)
        return self.__config
            

if __name__== '__main__':
    c = ConfigHelper('prod')
    print(c.get('telegram','bot_admins'))
