import datetime
import logging
import re

import arrow
import requests
from telegram import Update
from telegram.ext import CallbackContext, MessageHandler, Filters

from telegram_bot.config_util import ConfigHelper
from telegram_bot.handlers.handler_base import HandlerBase

c = ConfigHelper()
logger = logging.getLogger(__name__)

GEMINI_KEY = 'GEMINI'
GDAX_KEY = 'GDAX'
COINMARKETCAP_KEY = 'COINMARKETCAP'
TIME_KEY = 'TIME'


class CryptoQuotes(HandlerBase):

    def _get_with_timeout(self, url, timeout=5, headers=None, params=None):
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

    # def _get_gemini_quote(self, quote_name, *args, **kwargs):
    #     mapping = {"ETH": "ethusd", "BTC": "btcusd"}
    #     quote_name = mapping[quote_name]
    #
    #     # Get quotes from API
    #     url = f'https://api.gemini.com/v1/pubticker/{quote_name}'
    #     result = self._get_with_timeout(url)
    #     if result:
    #         return f"{GEMINI_KEY} : Bid: {result['bid']} Ask: {result['ask']}\n"
    #
    # def _get_gdax_quote(self, quote_name, *args, **kwargs):
    #     mapping = {"ETH": "ETH-USD", "BTC": "BTC-USD"}
    #
    #     quote_name = mapping[quote_name]
    #
    #     url = f'https://api.gdax.com/products/{quote_name}/book'
    #     result = self._get_with_timeout(url)
    #     if result:
    #         bid_price, bid_amount, _ = result['bids'][0]
    #         ask_price, ask_amount, _ = result['asks'][0]
    #
    #         return f"{GDAX_KEY} : Bid: {bid_price} Ask: {ask_price}\n"

    def _get_cryptowatch_quotes(self):
        resp = self._get_with_timeout('https://api.cryptowat.ch/markets/prices')
        # END REMOVE
        text = """"""
        for currency, exchanges in c.config['crypto']['prices'].items():
            ccy_text = f"""<b>{currency}<b>:\n"""
            for exchange in exchanges:
                exchange_desc = exchange.split(':')[1]  # keep only the exchange name
                ccy_text += f"\t{exchange_desc}:{resp['result'][exchange]}\n"
            text += ccy_text
        text += f"CW API Credits: {resp['allowance']['remaining']}\n---\n"
        return text

    def _get_cmc_data(self):
        rest_api_id = c.get('crypto', 'cmc_rest_api_id')

        msg = """"""
        cmc_headers = {'X-CMC_PRO_API_KEY': rest_api_id}
        url = 'https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest'
        result = self._get_with_timeout(url, headers=cmc_headers)

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
        cmc_result = self._get_with_timeout(url, headers=cmc_headers, params=params)
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

    def _get_current_quotes(self):
        key_func_mapping = {'CRYPTOWATCH': self._get_cryptowatch_quotes,
                            'COINMARKETCAP': self._get_cmc_data
                            }
        t = arrow.get(tzinfo='America/New_York').strftime("%Y-%m-%d %H:%m:%S%p")
        string_to_send = f"Time: {t}\n"

        for name, call_func in key_func_mapping.items():
            try:
                # calculate the result and store to cache
                result = call_func()
            except Exception as e:
                logger.exception(f"Exception for {name}")
                result = f"Failed to get for: {name}\n"
            finally:
                # construct the string
                string_to_send += result

        return string_to_send

    def get_current_quotes_handler(self, update: Update, context: CallbackContext):
        quotes_response = self._get_current_quotes()

        chat_id = update.effective_user.id
        context.bot.sendMessage(chat_id=chat_id, text=quotes_response)

    def _get_handlers(self):
        return [
            (MessageHandler, {'filters': Filters.private &
                                         Filters.regex(re.compile('^(quotes)', re.IGNORECASE)),
                              'callback': self.get_current_quotes_handler})
        ]

if __name__ =='__main__':
    # print(CryptoQuotes()._get_gdax_quote('ETH'))
    print(CryptoQuotes()._get_current_quotes())