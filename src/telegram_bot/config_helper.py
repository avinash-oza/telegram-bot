import json
import logging
import os
from typing import Any, Dict

import boto3
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class ConfigHelper:
    class _ConfigHelper:
        def __init__(self):
            self._env_name = os.environ["env_name"].lower()
            self.__config = None
            logger.info("Creating classes")

        def get(self, section, value):
            return self.config[section][value]

        @property
        def config(self) -> Dict[str, Any]:
            if self.__config is None:
                if self._env_name == "prod":
                    config_dict = self._read_config_from_s3()
                    self.__config = config_dict
                else:
                    logger.warning(
                        "Reading config from local file for non-prod environment"
                    )
                    config_dict = self._read_config_from_local_file()
                    self.__config = config_dict

            return self.__config

        def _read_config_from_local_file(self) -> Dict[str, Any]:
            config_path = f"../{self._env_name}.json"
            with open(config_path, "r") as f:
                return json.loads(f.read())

        def _read_config_from_s3(self) -> Dict[str, Any]:
            s3 = boto3.client("s3")
            config_bucket = os.environ["config_bucket"]
            config_key = f"telegram-bot/{self._env_name}.json"
            config_bytes = s3.get_object(Bucket=config_bucket, Key=config_key)["Body"]
            return json.load(config_bytes)

    instance = None

    def __init__(self):
        if not ConfigHelper.instance:
            ConfigHelper.instance = ConfigHelper._ConfigHelper()

    def __getattr__(self, name):
        return getattr(self.instance, name)
