from unittest import TestCase, mock

from requests import HTTPError

from src.telegram_bot.handlers.temperature_data import get_temperatures


@mock.patch("telegram_bot.temperature_data.os.environ.get", return_value="TEST_API_KEY")
class HandlersTestCase(TestCase):
    @mock.patch("telegram_bot.temperature_data.requests.get")
    @mock.patch("arrow.now")
    def test_get_temperatures(
        self, mock_arrow_now, mock_requests_get, mock_api_key, *_
    ):
        mock_arrow_now.return_value.strftime.return_value = "2019-01-01 10:10:00 PM"
        mock_requests_get.return_value.json.return_value = {
            "data": [{"timestamp": "2019-01-02T10:10:00", "value": "37"}]
        }
        resp_text = get_temperatures(["OUTDOOR"])

        self.assertEqual(
            resp_text,
            "Time: 2019-01-01 10:10:00 PM\nOUTDOOR: 37.00F -> 01/02 05:10:00 AM\n",
        )

    @mock.patch("telegram_bot.temperature_data.requests.get")
    @mock.patch("arrow.now")
    def test_get_temperatures_all(
        self, mock_arrow_now, mock_requests_get, mock_api_key, *_
    ):
        mock_arrow_now.return_value.strftime.return_value = "2019-01-01 10:10:00 PM"
        mock_requests_get.return_value.json.side_effect = [
            {"data": [{"timestamp": "2019-01-02T10:10:00", "value": "37"}]},
            {"data": []},
            {"data": []},
        ]
        resp_text = get_temperatures("ALL")

        self.assertEqual(
            resp_text,
            "Time: 2019-01-01 10:10:00 PM\nOUTDOOR: 37.00F -> 01/02 05:10:00 AM\nGARAGE: Could not get value\nAPARTMENT1: Could not get value\n",
        )

    @mock.patch("telegram_bot.temperature_data.requests.get")
    @mock.patch("arrow.now")
    def test_get_temperatures_all_good(
        self, mock_arrow_now, mock_requests_get, mock_api_key, *_
    ):
        mock_arrow_now.return_value.strftime.return_value = "2019-01-01 10:10:00 PM"
        mock_requests_get.return_value.json.side_effect = [
            {"data": [{"timestamp": "2019-01-02T10:10:00", "value": "37"}]},
            {"data": [{"timestamp": "2019-01-02T10:27:00", "value": "47"}]},
            {"data": [{"timestamp": "2019-01-02T10:29:00", "value": "46.1"}]},
        ]
        resp_text = get_temperatures("ALL")

        self.assertEqual(
            resp_text,
            "Time: 2019-01-01 10:10:00 PM\nOUTDOOR: 37.00F -> 01/02 05:10:00 AM\nGARAGE: 47.00F -> 01/02 05:27:00 AM\nAPARTMENT1: 46.10F -> 01/02 05:29:00 AM\n",
        )

    @mock.patch("telegram_bot.temperature_data.requests.get")
    @mock.patch("arrow.now")
    def test_get_temperatures_http_exception(
        self, mock_arrow_now, mock_requests_get, mock_api_key, *_
    ):
        mock_arrow_now.return_value.strftime.return_value = "2019-01-01 10:10:00 PM"
        mock_requests_get.return_value.raise_for_status.side_effect = HTTPError(
            "Test error"
        )
        resp_text = get_temperatures("ALL")

        self.assertEqual(
            resp_text,
            "Time: 2019-01-01 10:10:00 PM\nOUTDOOR: Exception on getting value\nGARAGE: Exception on getting value\nAPARTMENT1: Exception on getting value\n",
        )
