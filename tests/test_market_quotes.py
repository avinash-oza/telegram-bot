from unittest import TestCase, mock

from requests import HTTPError

from telegram_bot.handlers.market_quotes import get_coinmarketcap_data, get_current_quotes


@mock.patch('telegram_bot.market_quotes.os.environ.get', return_value='TEST_API_KEY')
class MarketQuotesTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cmc_global_response_dict = {
            "data": {
                "btc_dominance": 67.0057,
                "eth_dominance": 9.02205,
                "active_cryptocurrencies": 2941,
                "total_cryptocurrencies": 4637,
                "active_market_pairs": 21209,
                "active_exchanges": 445,
                "total_exchanges": 677,
                "last_updated": "2019-05-16T18:47:00.000Z",
                "quote": {
                    "USD": {
                        "total_market_cap": 250385096532.124,
                        "total_volume_24h": 119270642406.968,
                        "total_volume_24h_reported": 1514905418.39087,
                        "altcoin_volume_24h": 119270642406.968,
                        "altcoin_volume_24h_reported": 1514905418.39087,
                        "altcoin_market_cap": 250385096532.124,
                        "last_updated": "2019-05-16T18:47:00.000Z"
                    }
                }
            },
            "status": {
                "timestamp": "2019-11-24T10:08:53.596Z",
                "error_code": 0,
                "error_message": "",
                "elapsed": 10,
                "credit_count": 1
            }
        }
        cls.cmc_quote_response_dict = {
            "data": {
                "1": {
                    "id": 1,
                    "name": "Bitcoin",
                    "symbol": "BTC",
                    "slug": "bitcoin",
                    "circulating_supply": 17199862,
                    "total_supply": 17199862,
                    "max_supply": 21000000,
                    "date_added": "2013-04-28T00:00:00.000Z",
                    "num_market_pairs": 331,
                    "cmc_rank": 1,
                    "last_updated": "2018-08-09T21:56:28.000Z",
                    "tags": [
                        "mineable"
                    ],
                    "platform": None,
                    "quote": {
                        "USD": {
                            "price": 6602.60701122,
                            "volume_24h": 4314444687.5194,
                            "percent_change_1h": 0.988615,
                            "percent_change_24h": 4.37185,
                            "percent_change_7d": -12.1352,
                            "market_cap": 113563929433.21645,
                            "last_updated": "2018-08-09T21:56:28.000Z"
                        }
                    }
                },
                "1027": {
                    "id": 1,
                    "name": "Ethereum",
                    "symbol": "ETH",
                    "slug": "ethereum",
                    "circulating_supply": 17199862,
                    "total_supply": 17199862,
                    "max_supply": 21000000,
                    "date_added": "2013-04-28T00:00:00.000Z",
                    "num_market_pairs": 331,
                    "cmc_rank": 2,
                    "last_updated": "2018-08-09T21:56:28.000Z",
                    "tags": [
                        "mineable"
                    ],
                    "platform": None,
                    "quote": {
                        "USD": {
                            "price": 165.045,
                            "volume_24h": 634444680.5194,
                            "percent_change_1h": 0.988615,
                            "percent_change_24h": 4.37185,
                            "percent_change_7d": -12.1352,
                            "market_cap": 103563929433.21645,
                            "last_updated": "2018-08-09T21:56:28.000Z"
                        }
                    }
                }
            },
            "status": {
                "timestamp": "2019-11-24T10:08:53.596Z",
                "error_code": 0,
                "error_message": "",
                "elapsed": 10,
                "credit_count": 1
            }
        }

    @mock.patch('telegram_bot.market_quotes.get_with_timeout')
    @mock.patch('arrow.now')
    def test_get_coinmarketcap(self, mock_arrow_now, mock_get_with_timeout, mock_env):
        mock_get_with_timeout.side_effect = [self.cmc_global_response_dict, self.cmc_quote_response_dict]

        self.assertEqual(get_coinmarketcap_data(), 'MarketCap: 250B\nBTC Dom: 67.0057\nETH/BTC Vol Ratio: 0.147')

    @mock.patch('telegram_bot.market_quotes.get_with_timeout')
    @mock.patch('arrow.now')
    def test_get_coinmarketcap_missing_ticker(self, mock_arrow_now, mock_get_with_timeout, mock_env):
        mock_get_with_timeout.side_effect = [self.cmc_global_response_dict, {}]

        self.assertEqual(get_coinmarketcap_data(), 'MarketCap: 250B\nBTC Dom: 67.0057\nCould not calculate ratios')

    @mock.patch('telegram_bot.market_quotes.get_with_timeout')
    @mock.patch('arrow.now')
    def test_get_coinmarketcap_missing_all_tickers(self, mock_arrow_now, mock_get_with_timeout, mock_env):
        mock_get_with_timeout.side_effect = [self.cmc_global_response_dict, {}]

        self.assertEqual(get_coinmarketcap_data(), 'MarketCap: 250B\nBTC Dom: 67.0057\nCould not calculate ratios')

    @mock.patch('telegram_bot.market_quotes.get_with_timeout')
    @mock.patch('arrow.now')
    def test_get_coinmarketcap_missing_dominance(self, mock_arrow_now, mock_get_with_timeout, mock_env):
        mock_get_with_timeout.side_effect = [{}, {}]

        self.assertEqual(get_coinmarketcap_data(), 'Could not get Market Cap\nCould not calculate ratios')

    @mock.patch('telegram_bot.market_quotes.get_with_timeout')
    @mock.patch('arrow.now')
    def test_get_coinmarketcap_missing_api_key(self, mock_arrow_now, mock_get_with_timeout, mock_env):
        mock_env.return_value = None

        self.assertEqual(get_coinmarketcap_data(), 'Missing key for CMC')

@mock.patch('telegram_bot.market_quotes.os.environ.get', return_value='TEST_API_KEY')
class GetCurrentQuotesTestCase(TestCase):
    @mock.patch('telegram_bot.market_quotes.get_coinmarketcap_data')
    @mock.patch('telegram_bot.market_quotes.get_gemini_quote')
    @mock.patch('telegram_bot.market_quotes.get_gdax_quote')
    @mock.patch('telegram_bot.market_quotes.datetime.datetime')
    def test_get_current_quotes(self, mock_datetime, mock_get_gdax_quote, mock_get_gemini_quote, mock_get_coinmarketcap_data, mock_env):
        mock_datetime.today.return_value.strftime.return_value = 'TEST_DATETIME'
        mock_get_gdax_quote.return_value = 'GDAX_RESPONSE\n'
        mock_get_gemini_quote.return_value = 'GEMINI_RESPONSE\n'
        mock_get_coinmarketcap_data.return_value = 'CMC_RESPONSE\n'

        self.assertEqual(get_current_quotes(), 'Time: TEST_DATETIME\nGDAX_RESPONSE\nGEMINI_RESPONSE\nCMC_RESPONSE\n')

    @mock.patch('telegram_bot.market_quotes.get_coinmarketcap_data')
    @mock.patch('telegram_bot.market_quotes.get_gemini_quote')
    @mock.patch('telegram_bot.market_quotes.get_gdax_quote')
    @mock.patch('telegram_bot.market_quotes.datetime.datetime')
    def test_get_current_quotes_one_missing(self, mock_datetime, mock_get_gdax_quote, mock_get_gemini_quote, mock_get_coinmarketcap_data, mock_env):
        mock_datetime.today.return_value.strftime.return_value = 'TEST_DATETIME'
        mock_get_gdax_quote.return_value = 'GDAX_RESPONSE\n'
        mock_get_gemini_quote.side_effect = HTTPError('API error')
        mock_get_coinmarketcap_data.return_value = 'CMC_RESPONSE\n'

        self.assertEqual(get_current_quotes(), 'Time: TEST_DATETIME\nGDAX_RESPONSE\nFailed to get for exchange GEMINI\nCMC_RESPONSE\n')
