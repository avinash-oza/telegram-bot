import json
import logging
import os

import boto3

logger = logging.getLogger(__name__)


class ConfigHelper:
    class _ConfigHelper:
        def __init__(self):
            self._s3 = boto3.client("s3")
            self._env_name = os.environ["env_name"].lower()
            self._config_bucket = os.environ["config_bucket"]
            self.__config = None
            logger.info("Creating class")

        def get(self, section, value):
            return self.config[section][value]

        @property
        def config(self):
            if self.__config is None:
                config_key = f"telegram-bot/{self._env_name}.json"
                config_bytes = self._s3.get_object(
                    Bucket=self._config_bucket, Key=config_key
                )["Body"]
                self.__config = json.load(config_bytes)
            return self.__config

    instance = None

    def __init__(self):
        if not ConfigHelper.instance:
            ConfigHelper.instance = ConfigHelper._ConfigHelper()

    def __getattr__(self, name):
        return getattr(self.instance, name)
