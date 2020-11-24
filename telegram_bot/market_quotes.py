import datetime
import logging

import requests
from telegram_bot.config_util import ConfigHelper

c = ConfigHelper()
logger = logging.getLogger(__name__)

GEMINI_KEY = 'GEMINI'
GDAX_KEY = 'GDAX'
COINMARKETCAP_KEY = 'COINMARKETCAP'
TIME_KEY = 'TIME'


def get_with_timeout(url, timeout=5, headers=None, params=None):
    """
    Gets data with a timeout. When there is no reply, and empty dict is returned
    :param url:
    :param timeout:
    :param error_message:
    :return:
    """
    try:
        r = requests.get(url, timeout=timeout, headers=headers, params=params)
        r.raise_for_status()
        result = r.json()
    except requests.HTTPError as e:
        logger.exception("Could not get quotes")
        return {}
    else:
        return result


def get_gemini_quote(quote_name, *args, **kwargs):
    mapping = {"ETH": "ethusd", "BTC": "btcusd"}
    quote_name = mapping[quote_name]

    # Get quotes from API
    url = f'https://api.gemini.com/v1/pubticker/{quote_name}'
    result = get_with_timeout(url)
    if result:
        return f"{GEMINI_KEY} : Bid: {result['bid']} Ask: {result['ask']}\n"


def get_gdax_quote(quote_name, *args, **kwargs):
    mapping = {"ETH": "ETH-USD", "BTC": "BTC-USD"}

    quote_name = mapping[quote_name]

    url = f'https://api.gdax.com/products/{quote_name}/book'
    result = get_with_timeout(url)
    if result:
        bid_price, bid_amount, _ = result['bids'][0]
        ask_price, ask_amount, _ = result['asks'][0]

        return f"{GDAX_KEY} : Bid: {bid_price} Ask: {ask_price}\n"


def get_coinmarketcap_data(*args, **kwargs):
    rest_api_id = c.get('crypto', 'cmc_rest_api_id')

    msg = """"""
    cmc_headers = {'X-CMC_PRO_API_KEY': rest_api_id}
    url = 'https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest'
    result = get_with_timeout(url, headers=cmc_headers)

    if result:
        total_market_cap = result['data']['quote']['USD']['total_market_cap']
        bitcoin_percent_dominance = result['data']['btc_dominance']
        msg += "MarketCap: {0:d}B\n".format(int(total_market_cap / 1000000000))
        msg += f"BTC Dom: {bitcoin_percent_dominance}\n"
    else:
        msg += "Could not get Market Cap\n"

    # Get volume of ETH and BTC
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest'
    symbol_id_to_slug = {'1': 'bitcoin', '1027': 'ethereum'}
    params = {'id': ','.join(symbol_id_to_slug.keys())}
    cmc_result = get_with_timeout(url, headers=cmc_headers, params=params)
    if not result:
        logger.warning(f"Could not get CMC data for symbols")

    results = {}

    if cmc_result and 'data' in cmc_result:
        for symbol_id, symbol_dict in cmc_result['data'].items():
            try:
                slug = symbol_id_to_slug[symbol_id]
            except KeyError:
                logger.warning(f"Ignoring response id {symbol_id}")
                continue
            symbol = symbol_dict['symbol']
            quotes = symbol_dict['quote']['USD']
            results[slug] = {'symbol': symbol, 'volume_24h': quotes['volume_24h']}

    if len(results) == 2:
        # received all of the metrics to calculate
        btc_volume = results['bitcoin']['volume_24h']
        eth_volume = results['ethereum']['volume_24h']
        eth_btc_volume_ratio = float(eth_volume) / float(btc_volume)
        msg += "ETH/BTC Vol Ratio: {0:.3f}".format(eth_btc_volume_ratio)

    else:
        msg += "Could not calculate ratios"

    return msg


def get_current_quotes(quote_name='ETH'):
    key_func_mapping = {(GDAX_KEY, quote_name): get_gdax_quote,
                        (GEMINI_KEY, quote_name): get_gemini_quote,
                        (COINMARKETCAP_KEY, quote_name): get_coinmarketcap_data
                        }
    string_to_send = "Time: {0}\n".format(datetime.datetime.today().strftime("%Y-%m-%d %H:%m:%S"))

    for key, call_func in key_func_mapping.items():
        exchange, pair = key
        try:
            # calculate the result and store to cache
            result = call_func(quote_name=quote_name)
        except Exception as e:
            logger.exception("Exception for {}".format(key))
            result = f"Failed to get for exchange {exchange}\n"
        finally:
            # construct the string
            string_to_send += result

    return string_to_send

# f __name__ == '__main__':
#   print(get_current_quotes('BTC'))
