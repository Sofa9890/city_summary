import unittest
from unittest.mock import patch

from clients.rates import get_rate
from clients.weather import get_weather
from exceptions import (
    CityNotFoundError,
    CurrencyNotFoundError,
    HttpStatusError,
    InputError,
    InvalidResponseError,
)

LOCATION = {"results": [{"latitude": 55.75, "longitude": 37.62}]}


class WeatherTests(unittest.TestCase):
    @patch("clients.weather.get_json")
    def test_weather_is_normalized(self, get_json):
        get_json.side_effect = [
            LOCATION,
            {"current": {"temperature_2m": -3.2, "weather_code": 0}},
        ]
        self.assertEqual(get_weather("Moscow"), {"temp_c": -3.2, "description": "ясно"})
        self.assertEqual(get_json.call_count, 2)

    @patch("clients.weather.get_json")
    def test_missing_city(self, get_json):
        for payload in ({"results": []}, {"generationtime_ms": 0.1}):
            with self.subTest(payload=payload):
                get_json.return_value = payload
                with self.assertRaises(CityNotFoundError):
                    get_weather("NoSuchCity")

    @patch("clients.weather.get_json")
    def test_bad_geocoding_is_rejected(self, get_json):
        for payload in (
            {"results": "wrong"},
            {"results": [None]},
            {"results": [{"latitude": True, "longitude": 0}]},
            {"results": [{"latitude": 91, "longitude": 0}]},
            {"error": True},
        ):
            with self.subTest(payload=payload):
                get_json.return_value = payload
                with self.assertRaises(InvalidResponseError):
                    get_weather("Moscow")

    @patch("clients.weather.get_json")
    def test_bad_temperature_is_rejected(self, get_json):
        for temperature in (None, "cold", True, float("nan"), float("inf")):
            with self.subTest(temperature=temperature):
                get_json.side_effect = [
                    LOCATION,
                    {"current": {"temperature_2m": temperature, "weather_code": 0}},
                ]
                with self.assertRaises(InvalidResponseError):
                    get_weather("Moscow")

    @patch("clients.weather.get_json")
    def test_bad_forecast_structure_or_code_is_rejected(self, get_json):
        for forecast in (
            {},
            {"current": []},
            {"current": {"temperature_2m": 10, "weather_code": 999}},
        ):
            with self.subTest(forecast=forecast):
                get_json.side_effect = [LOCATION, forecast]
                with self.assertRaises(InvalidResponseError):
                    get_weather("Moscow")


class RateTests(unittest.TestCase):
    @patch("clients.rates.get_json")
    def test_rate_and_currency_normalization(self, get_json):
        get_json.return_value = {"base": "EUR", "quote": "RUB", "rate": 99.5}
        self.assertEqual(get_rate(" eur "), 99.5)
        get_json.assert_called_once_with("https://api.frankfurter.dev/v2/rate/EUR/RUB")

    @patch("clients.rates.get_json")
    def test_currency_not_found_statuses(self, get_json):
        for status in (400, 404, 422):
            with self.subTest(status=status):
                get_json.side_effect = HttpStatusError(status)
                with self.assertRaises(CurrencyNotFoundError):
                    get_rate("ZZZ")

    @patch("clients.rates.get_json")
    def test_wrong_pair_or_rate_is_rejected(self, get_json):
        invalid = [None, True, "90", 0, -5, float("nan"), float("inf")]
        for value in invalid:
            with self.subTest(value=value):
                get_json.return_value = {"base": "USD", "quote": "RUB", "rate": value}
                with self.assertRaises(InvalidResponseError):
                    get_rate("USD")
        get_json.return_value = {"base": "EUR", "quote": "RUB", "rate": 90}
        with self.assertRaises(InvalidResponseError):
            get_rate("USD")

    @patch("clients.rates.get_json")
    def test_invalid_currency_format_makes_no_request(self, get_json):
        for currency in ("", "EURO", "123", "РУБ"):
            with self.subTest(currency=currency), self.assertRaises(InputError):
                get_rate(currency)
        get_json.assert_not_called()
