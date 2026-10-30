import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from exceptions import (
    CityNotFoundError,
    CurrencyNotFoundError,
    InvalidResponseError,
    ServiceUnavailableError,
)
from main import main

SUMMARY = {
    "city": "Moscow",
    "weather": {"temp_c": -3.2, "description": "ясно", "warm_clothes": True},
    "rates": {"currency": "USD", "rate_to_rub": 92.15, "expensive": False},
}


class CliTests(unittest.TestCase):
    @patch("main.build_city_summary", return_value=SUMMARY)
    def test_success_text_and_default_currency(self, build):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(main(["--city", "Moscow"]), 0)
        self.assertIn("Тёплая одежда: да", stdout.getvalue())
        self.assertIn("USD→RUB: 92.15", stdout.getvalue())
        build.assert_called_once_with("Moscow", "USD")

    @patch("main.build_city_summary", return_value=SUMMARY)
    def test_json_is_valid_and_has_no_extra_text(self, build):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(main(["--city", "Moscow", "--json"]), 0)
        self.assertEqual(json.loads(stdout.getvalue()), SUMMARY)

    def test_exit_codes_and_errors_use_stderr(self):
        for error, expected in (
            (CityNotFoundError("город"), 3),
            (CurrencyNotFoundError("валюта"), 3),
            (ServiceUnavailableError("сеть"), 4),
            (InvalidResponseError("данные"), 4),
        ):
            with (
                self.subTest(error=error),
                patch("main.build_city_summary", side_effect=error),
            ):
                stdout, stderr = io.StringIO(), io.StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    self.assertEqual(main(["--city", "Moscow"]), expected)
                self.assertEqual(stdout.getvalue(), "")
                self.assertIn("Ошибка:", stderr.getvalue())
                self.assertNotIn("Traceback", stderr.getvalue())

    def test_missing_required_argument_exits_with_2(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main([])
        self.assertEqual(caught.exception.code, 2)

    def test_invalid_values_exit_with_2_without_network(self):
        for arguments in (["--city", " "], ["--city", "Moscow", "--currency", "123"]):
            with (
                self.subTest(arguments=arguments),
                patch("clients.http.requests.get") as get,
                redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(main(arguments), 2)
                get.assert_not_called()
