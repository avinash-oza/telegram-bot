import datetime
import json
import logging
import urllib.request

from expiringdict import ExpiringDict

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) #TODO: Remove this later on

#TODO: rewrite this using requests

cache = ExpiringDict(max_len=10, max_age_seconds=15)
market_cap_cache = ExpiringDict(max_len=10, max_age_seconds=60*5) # 5 mins

def get_gemini_quote(quote_name):
    mapping = {"ETH": "ethusd",
               "BTC": "btcusd"}
    quote_name = mapping[quote_name]

    GEMINI_STR = "GEMINI_STR"
    if cache.get(GEMINI_STR):
        logger.info("Got hit for cache for exchange GEMINI")
        return cache.get(GEMINI_STR)

    url = 'https://api.gemini.com/v1/pubticker/{0}'.format(quote_name)
    try:
        result = json.load(urllib.request.urlopen(url))
    except Exception as e:
        logger.exception("Could not get quote from exchange")
        return "Gemini", "", "Could not get quote from Gemini"

    bid_price = result['bid']
    ask_price = result['ask']

    quote_details = "Gemini", bid_price, ask_price

    # Store string into cache
    cache[GEMINI_STR] = quote_details

    return quote_details

def get_gdax_quote(quote_name):
        GDAX_STR = "GDAX_STR"
        mapping = {"ETH" : "ETH-USD",
                   "BTC" : "BTC-USD"}

        quote_name = mapping[quote_name]
        if cache.get(GDAX_STR):
            logger.info("Got hit for cache on exchange {}".format(GDAX_STR))
            return cache.get(GDAX_STR)

        url = 'https://api.gdax.com/products/{0}/book'.format(quote_name)
        try:
            result = json.load(urllib.request.urlopen(url))
        except Exception as e:
            logger.exception("Could not get quote from exchange")
            return "GDAX", "", "Could not get quote from GDAX"

        bid_price, bid_amount, _ = result['bids'][0]
        ask_price, ask_amount, _ = result['asks'][0]

        quote_details = "GDAX", bid_price, ask_price

        # Store string into cache
        cache[GDAX_STR] = quote_details

        return quote_details


def get_coinmarketcap_data():
    COINMARKETCAP_STR = "COINMARKETCAP_STR"
    if market_cap_cache.get(COINMARKETCAP_STR):
        logger.info("Got hit for cache COINMARKETCAP")
        return market_cap_cache.get(COINMARKETCAP_STR)

    url = 'https://api.coinmarketcap.com/v1/global/'
    try:
        result = json.load(urllib.request.urlopen(url))
    except Exception as e:
        logger.exception("Could not get quote from exchange COINMARKETCAP")
        return "CoinMarketCap", "", "Could not get info from CoinMarketCap"

    total_market_cap = result['total_market_cap_usd']
    bitcoin_percent_dominance = result['bitcoin_percentage_of_market_cap']

    # Get volume of ETH and BTC
    url = 'https://api.coinmarketcap.com/v1/ticker/{0}'
    tickers_to_get = ['bitcoin', 'ethereum']
    results = []

    for ticker in tickers_to_get:
        try:
            results.append(json.load(urllib.request.urlopen(url.format(ticker))))
        except Exception as e:
            logger.exception("Could not get quote from exchange COINMARKETCAP")
            return "CoinMarketCap", "", "Could not get info from CoinMarketCap"

    btc_result, ethereum_result = results
    btc_volume = btc_result[0]['24h_volume_usd']
    eth_volume = ethereum_result[0]['24h_volume_usd']
    eth_btc_volume_ratio = float(eth_volume) / float(btc_volume)

    final_result = (total_market_cap, bitcoin_percent_dominance, eth_btc_volume_ratio)

    market_cap_cache[COINMARKETCAP_STR] = final_result

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
