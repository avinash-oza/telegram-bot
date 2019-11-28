import datetime
import logging

import requests
from expiringdict import ExpiringDict

logger = logging.getLogger(__name__)

cache = ExpiringDict(max_len=10, max_age_seconds=60 * 5)

GEMINI_KEY = 'GEMINI'
GDAX_KEY = 'GDAX'
COINMARKETCAP_KEY = 'COINMARKETCAP'
TIME_KEY = 'TIME'


def get_with_timeout(url, timeout=5):
    """
    Gets data with a timeout. When there is no reply, and empty dict is returned
    :param url:
    :param timeout:
    :param error_message:
    :return:
    """
    try:
        r = requests.get(url, timeout=timeout)
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
    url = 'https://api.coinmarketcap.com/v1/global/'
    try:
        r = requests.get(url)
        r.raise_for_status()
        result = r.json()
    except requests.HTTPError as e:
        logger.exception("Could not get quote from {}".format(COINMARKETCAP_KEY))
        raise

    total_market_cap = result['total_market_cap_usd']
    bitcoin_percent_dominance = result['bitcoin_percentage_of_market_cap']

    # Get volume of ETH and BTC
    url = 'https://api.coinmarketcap.com/v1/ticker/{0}'
    tickers_to_get = ['bitcoin', 'ethereum']
    results = []

    for ticker in tickers_to_get:
        try:
            r = requests.get(url.format(ticker))
            r.raise_for_status()
            result = r.json()
            results.append(result)
        except Exception as e:
            logger.exception("Could not get quote from exchange COINMARKETCAP")

    btc_result, ethereum_result = results
    btc_volume = btc_result[0]['24h_volume_usd']
    eth_volume = ethereum_result[0]['24h_volume_usd']
    eth_btc_volume_ratio = float(eth_volume) / float(btc_volume)

    return "MarketCap: {0:d}B BTC Dom: {1} ETH/BTC Vol Ratio:{2:.2f}".format(
        int(total_market_cap / 1000000000), bitcoin_percent_dominance, eth_btc_volume_ratio)


def get_current_quotes(quote_name='ETH'):
    key_func_mapping = {(GDAX_KEY, quote_name): get_gdax_quote,
                        (GEMINI_KEY, quote_name): get_gemini_quote,
#                       (COINMARKETCAP_KEY, quote_name): get_coinmarketcap_data
                        }
    # cache the time as well
    try:
        string_to_send = cache[TIME_KEY]
    except KeyError:
        string_to_send = "Time: {0}\n".format(datetime.datetime.today().strftime("%Y-%m-%d %H:%m:%S"))
        cache[TIME_KEY] = string_to_send

    for key, call_func in key_func_mapping.items():
        try:
            # check if the key is in the cache
            result = cache[key]
        except KeyError:
            try:
                # calculate the result and store to cache
                result = call_func(quote_name=quote_name)
                cache[key] = result
            except Exception as e:
                logger.exception("Exception for {}".format(key))
                result = "Failed to get for exchange {}".format(key)
        finally:
            # construct the string
            string_to_send += result

    return string_to_send

# if __name__ == '__main__':
#     print(get_gdax_quote('ETH'))
