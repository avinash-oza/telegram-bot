import logging
import re

import arrow
import boto3
import requests
from telegram import Update
from telegram.ext import CallbackContext, MessageHandler, Filters

from telegram_bot.config_helper import ConfigHelper
from telegram_bot.handlers.handler_base import HandlerBase

c = ConfigHelper()
logger = logging.getLogger(__name__)


class Temperatures(HandlerBase):

    def get_temperatures(self, locations='ALL'):
        if locations == 'ALL':
            locations = c.get('temperature', 'locations')

        dt_format = '%Y-%m-%d %I:%M:%S %p'
        current_time = arrow.now().strftime(dt_format)

        s = requests.Session()
        s.headers.update({'X-Api-Key': c.get('temperature', 'api_key')})
        url = c.get('temperature', 'url')

        resp_text = f"""Time: {current_time}\n"""
        for loc in locations:
            try:
                resp = s.get(fr'{url}/temperatures/{loc}/today?limit=1')
                resp.raise_for_status()
            except requests.exceptions.HTTPError:
                logger.exception(f"Error when getting {loc}")
                resp_text += f"{loc}: Exception on getting value\n"
            else:
                r = resp.json()
                logger.info(f"Response is {r}")
                if 'data' in r and r['data']:
                    data = r['data'][0]
                    value = float(data['value'])
                    ts = arrow.get(data['timestamp']).to('America/New_York').strftime('%m/%d %I:%M:%S %p')
                    resp_text += f"{loc}: {value:.2f}F -> {ts}\n"
                else:
                    resp_text += f"{loc}: Could not get value\n"
        return resp_text

    def get_temperature_chart(self):
        # return the latest temperature chart url
        params = c.config['temperature']['chart']
        bucket = params['bucket_name']
        key = params['key']
        s3 = boto3.client('s3')

        params_kwargs = {'Bucket': bucket,
                         'Key': key,
                         }

        image_url = s3.generate_presigned_url('get_object',
                                              Params=params_kwargs,
                                              ExpiresIn=60)
        return image_url

    def temperatures_handler(self, update: Update, context: CallbackContext):
        try:
            msg = self.get_temperatures()
        except Exception as e:
            logger.exception("Error occurred getting temperatures")
            msg = "An error occurred while trying to get temperatures"

        chat_id = update.effective_user.id
        context.bot.sendMessage(chat_id=chat_id, text=msg)

    def charts_handler(self, update: Update, context: CallbackContext):
        chart_type_mapping = {'temps': self.get_temperature_chart}
        command_args = update.effective_message.text.lower().lstrip('charts ')
        chart_name = "temps" if not command_args else command_args

        chat_id = update.effective_user.id

        try:
            chart_url = chart_type_mapping[chart_name]()
        except Exception as e:
            msg = f"Error occurred getting {chart_name} chart"
            logger.exception(msg)
            context.bot.sendMessage(chat_id=chat_id, text=msg)
        else:
            context.bot.sendPhoto(chat_id=chat_id, photo=chart_url)

    def _get_handlers(self):
        return [
            (
                MessageHandler, {'filters': Filters.private &
                                            Filters.regex(re.compile('^(charts)', re.IGNORECASE)),
                                 'callback': self.charts_handler}
            ),
            (
                MessageHandler, {'filters': Filters.private &
                                            Filters.regex(re.compile('^(temps)', re.IGNORECASE)),
                                 'callback': self.temperatures_handler}
            )
        ]
