import datetime
import logging
import os

import requests

logger = logging.getLogger(__name__)


def get_temperatures(locations='ALL'):
    rest_api_id = os.environ.get('TELEGRAM_TEMP_REST_API_ID')
    if rest_api_id is None:
        logger.error("No TELEGRAM_TEMP_REST_API_ID set.")
        return None

    if locations == 'ALL':
        locations = ['OUTDOOR', 'GARAGE']

    current_time = datetime.datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
    resp_text = f"""Time:{current_time}\n"""
    for loc in locations:
        try:
            resp = requests.get(fr'https://{rest_api_id}.execute-api.us-east-1.amazonaws.com/dev/temperatures/{loc}/today?limit=1', timeout=2)
            resp.raise_for_status()
        except requests.exceptions.HTTPError:
            logger.exception(f"Error when getting {loc}")
        else:
            r = resp.json()
            logger.info(f"Response is {r}")
            resp_text += f"{loc}: {r['data'][0]['value']}F\n"
    return resp_text
