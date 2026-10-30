import unittest
from unittest.mock import patch

from processing.preprocessing import is_expensive, needs_warm_clothes
from processing.service import build_city_summary


class ProcessingTests(unittest.TestCase):
    def test_threshold_boundaries(self):
        self.assertTrue(needs_warm_clothes(-0.1))
        self.assertFalse(needs_warm_clothes(0))
        self.assertFalse(needs_warm_clothes(5))
        self.assertTrue(is_expensive(100.01))
        self.assertFalse(is_expensive(100))
        self.assertFalse(is_expensive(90))

    @patch(
        "processing.service.get_weather",
        return_value={"temp_c": -3.2, "description": "ясно"},
    )
    @patch("processing.service.get_rate", return_value=101.5)
    def test_summary_schema_and_flags(self, get_rate, get_weather):
        summary = build_city_summary(" Moscow ", " eur ")
        self.assertEqual(
            summary,
            {
                "city": "Moscow",
                "weather": {
                    "temp_c": -3.2,
                    "description": "ясно",
                    "warm_clothes": True,
                },
                "rates": {"currency": "EUR", "rate_to_rub": 101.5, "expensive": True},
            },
        )
        get_rate.assert_called_once_with("EUR")
        get_weather.assert_called_once_with("Moscow")
