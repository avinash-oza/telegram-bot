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

    def _get_cryptowatch_quotes(self):
        resp = self._get_with_timeout('https://api.cryptowat.ch/markets/prices')
        text = """"""
        for currency, exchanges in c.config['crypto']['prices'].items():
            ccy_text = f"""<b>{currency}</b>:\n"""
            for exchange in exchanges:
                exchange_desc = exchange.split(':')[1]  # keep only the exchange name
                ccy_text += f"\t{exchange_desc}: {resp['result'][exchange]}\n"
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
            volume_24h = result['data']['quote']['USD']['total_volume_24h']
            btc_pct_dom = round(result['data']['btc_dominance'], 2)
            eth_pct_dom = round(result['data']['eth_dominance'], 2)

            msg += "<b>Total</b>:\n\tMarketCap: {0:d}B\n\tVolume(24H): {1:d}B\n".format(
                int(total_market_cap / 1000000000),
                int(volume_24h / 1000000000))
            msg += f"<b>Dominance</b>:\n\tBTC: {btc_pct_dom}%\n\tETH: {eth_pct_dom}%\n"
        else:
            msg += "Could not get Market Cap\n"

        # Get volume of ETH and BTC
        url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest'
        id_to_slug = c.config['crypto']['cmc']['id_slug_mapping']
        params = {'id': ','.join(id_to_slug.keys())}
        cmc_result = self._get_with_timeout(url, headers=cmc_headers, params=params)
        if not result:
            logger.warning(f"Could not get CMC data for symbols")

        results = {}

        if cmc_result and 'data' in cmc_result:
            for symbol_id, symbol_dict in cmc_result['data'].items():
                try:
                    slug = id_to_slug[symbol_id]
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

    def _build_response(self):
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

    def _handle_message(self, update: Update, context: CallbackContext):
        quotes_response = self._build_response()

        chat_id = update.effective_user.id
        context.bot.sendMessage(chat_id=chat_id, text=quotes_response)

    def _get_handlers(self):
        return [
            (MessageHandler, {'filters': Filters.private &
                                         Filters.regex(re.compile('^(quotes)', re.IGNORECASE)),
                              'callback': self._handle_message})
        ]
