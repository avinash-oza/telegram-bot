import logging
import boto3
import arrow
import requests
from telegram_bot.config_util import ConfigHelper

c = ConfigHelper()
logger = logging.getLogger(__name__)


def get_temperatures(locations='ALL'):
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


def get_temperature_chart():
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
