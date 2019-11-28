from unittest import TestCase, mock

from telegram_bot.temperature_data import get_temperatures


@mock.patch('telegram_bot.temperature_data.os.environ.get', return_value='TEST_API_KEY')
class HandlersTestCase(TestCase):

    @mock.patch('telegram_bot.temperature_data.requests.get')
    @mock.patch('arrow.now')
    def test_get_temperatures(self, mock_arrow_now, mock_requests_get, mock_api_key, *_):
        mock_arrow_now.return_value.strftime.return_value = '2019-01-01 10:10:00 PM'
        mock_requests_get.return_value.json.return_value = {
            'data': [{'timestamp': '2019-01-02T10:10:00', 'value': '37'}]}
        resp_text = get_temperatures(['OUTDOOR'])

        self.assertEqual(resp_text, "Time: 2019-01-01 10:10:00 PM\nOUTDOOR: 37F -> 01/02 05:10:00 AM\n")

    @mock.patch('telegram_bot.temperature_data.requests.get')
    @mock.patch('arrow.now')
    def test_get_temperatures_all(self, mock_arrow_now, mock_requests_get, mock_api_key, *_):
        mock_arrow_now.return_value.strftime.return_value = '2019-01-01 10:10:00 PM'
        mock_requests_get.return_value.json.side_effect = [
            {'data': [{'timestamp': '2019-01-02T10:10:00', 'value': '37'}]},
            {'data': []},
        ]
        resp_text = get_temperatures('ALL')

        self.assertEqual(resp_text,
                         "Time: 2019-01-01 10:10:00 PM\nOUTDOOR: 37F -> 01/02 05:10:00 AM\nGARAGE: Could not get value\n")

    @mock.patch('telegram_bot.temperature_data.requests.get')
    @mock.patch('arrow.now')
    def test_get_temperatures_all_good(self, mock_arrow_now, mock_requests_get, mock_api_key, *_):
        mock_arrow_now.return_value.strftime.return_value = '2019-01-01 10:10:00 PM'
        mock_requests_get.return_value.json.side_effect = [
            {'data': [{'timestamp': '2019-01-02T10:10:00', 'value': '37'}]},
            {'data': [{'timestamp': '2019-01-02T10:27:00', 'value': '47'}]},
        ]
        resp_text = get_temperatures('ALL')

        self.assertEqual(resp_text,
                         "Time: 2019-01-01 10:10:00 PM\nOUTDOOR: 37F -> 01/02 05:10:00 AM\nGARAGE: 47F -> 01/02 05:27:00 AM\n")
