import logging
import os

import arrow
import requests

logger = logging.getLogger(__name__)


def get_temperatures(locations='ALL'):
    rest_api_id = os.environ.get('TELEGRAM_TEMP_REST_API_ID')
    if rest_api_id is None:
        logger.error("No TELEGRAM_TEMP_REST_API_ID set.")
        return None

    if locations == 'ALL':
        locations = ['OUTDOOR', 'GARAGE','APARTMENT1']

    dt_format = '%Y-%m-%d %I:%M:%S %p'
    current_time = arrow.now().strftime(dt_format)

    resp_text = f"""Time: {current_time}\n"""
    for loc in locations:
        try:
            resp = requests.get(fr'https://{rest_api_id}.execute-api.us-east-1.amazonaws.com/dev/temperatures/{loc}/today?limit=1', timeout=2)
            resp.raise_for_status()
        except requests.exceptions.HTTPError:
            logger.exception(f"Error when getting {loc}")
            resp_text += f"{loc}: Exception on getting value\n"
        else:
            r = resp.json()
            logger.info(f"Response is {r}")
            if 'data' in r and r['data']:
                data = r['data'][0]
                value = data['value']
                ts = arrow.get(data['timestamp']).to('America/New_York').strftime('%m/%d %I:%M:%S %p')
                resp_text += f"{loc}: {value}F -> {ts}\n"
            else:
                resp_text += f"{loc}: Could not get value\n"
    return resp_text
