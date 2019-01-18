import datetime
import logging

import requests
from expiringdict import ExpiringDict

logger = logging.getLogger(__name__)

cache = ExpiringDict(max_len=10, max_age_seconds=15)
market_cap_cache = ExpiringDict(max_len=10, max_age_seconds=60*5) # 5 mins
GEMINI_KEY = 'GEMINI'
GDAX_KEY = 'GDAX'
COINMARKETCAP_KEY = 'COINMARKETCAP'

def get_gemini_quote(quote_name):
    mapping = {"ETH": "ethusd",
               "BTC": "btcusd"}
    quote_name = mapping[quote_name]

    try:
        return cache[GEMINI_KEY]
    except KeyError:
        logger.info("Did not get a hit for {}".format(GEMINI_KEY))
        # handle this below

    # Get quotes from API
    url = 'https://api.gemini.com/v1/pubticker/{0}'.format(quote_name)
    try:
        r = requests.get(url)
        r.raise_for_status()
        result = r.json()
    except requests.HTTPError as e:
        logger.exception("Could not get quote from exchange")
        raise
    else:
        # Store string into cache
        cache[GEMINI_KEY] = GEMINI_KEY, result['bid'], result['ask']

        return cache[GEMINI_KEY]

def get_gdax_quote(quote_name):
        GDAX_STR = "GDAX_STR"
        mapping = {"ETH" : "ETH-USD",
                   "BTC" : "BTC-USD"}

        quote_name = mapping[quote_name]
        try:
            return cache[GDAX_KEY]
        except KeyError:
            logger.info("Did not get a hit for {}".format(GDAX_KEY))


        url = 'https://api.gdax.com/products/{0}/book'.format(quote_name)
        try:
            r = requests.get(url)
            r.raise_for_status()
            result = r.json()
        except requests.HTTPError as e:
            logger.exception("Could not get quote from exchange")
            raise

        bid_price, bid_amount, _ = result['bids'][0]
        ask_price, ask_amount, _ = result['asks'][0]

        quote_details = GDAX_KEY, bid_price, ask_price

        # Store string into cache
        cache[GDAX_STR] = quote_details

        return quote_details


def get_coinmarketcap_data():
    try:
        return cache[COINMARKETCAP_KEY]
    except KeyError:
        logger.info("Did not get a hit for {}".format(COINMARKETCAP_KEY))

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
            return "CoinMarketCap", "", "Could not get info from CoinMarketCap"

    btc_result, ethereum_result = results
    btc_volume = btc_result[0]['24h_volume_usd']
    eth_volume = ethereum_result[0]['24h_volume_usd']
    eth_btc_volume_ratio = float(eth_volume) / float(btc_volume)

    final_result = (total_market_cap, bitcoin_percent_dominance, eth_btc_volume_ratio)

    market_cap_cache[COINMARKETCAP_KEY] = final_result

    return final_result


def get_current_quotes(quote_name='ETH'):

    prices_to_get = [get_gdax_quote, get_gemini_quote]
    string_to_send = "Time: {0}\n".format(datetime.datetime.today().strftime("%Y-%m-%d %H:%m:%S"))

    for one_exchange in prices_to_get:
        exchange_name, bid_price, ask_price = one_exchange(quote_name)
        string_to_send += "{0} : Bid: {1} Ask: {2}\n".format(exchange_name, bid_price, ask_price)

    total_marketcap, btc_dominance, eth_btc_volume_ratio = get_coinmarketcap_data()

    string_to_send += "MarketCap: {0:d}B BTC Dom: {1} ETH/BTC Vol Ratio:{2:.2f}".format(
        int(total_marketcap / 1000000000), btc_dominance, eth_btc_volume_ratio)

    return string_to_send
