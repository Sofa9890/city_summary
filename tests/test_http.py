import unittest
from unittest.mock import Mock, call, patch

import requests

from clients.http import get_json
from exceptions import HttpStatusError, InvalidResponseError, ServiceUnavailableError


def make_response(status=200, payload=None, headers=None):
    response = Mock(spec=requests.Response)
    response.status_code = status
    response.headers = headers or {}
    response.json.return_value = payload
    return response


class HttpTests(unittest.TestCase):
    @patch("clients.http.requests.get")
    def test_success_uses_get_timeout_and_closes_response(self, get):
        response = make_response(payload={"rate": 90})
        get.return_value = response
        self.assertEqual(get_json("https://example.test", {"x": 1}), {"rate": 90})
        self.assertEqual(get.call_args.kwargs["timeout"], 8)
        self.assertEqual(get.call_args.kwargs["params"], {"x": 1})
        self.assertTrue(get.call_args.kwargs["stream"])
        response.close.assert_called_once()

    def test_timeout_and_connection_error_have_two_retries(self):
        for error in (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            with (
                self.subTest(error=error.__name__),
                patch("clients.http.requests.get") as get,
                patch("clients.http.time.sleep") as sleep,
            ):
                get.side_effect = [
                    error("first"),
                    error("second"),
                    make_response(payload={}),
                ]
                self.assertEqual(get_json("https://example.test"), {})
                self.assertEqual(get.call_count, 3)
                self.assertEqual(sleep.call_args_list, [call(1), call(2)])

    def test_temporary_statuses_have_two_retries(self):
        for status in (500, 502, 503, 504):
            with (
                self.subTest(status=status),
                patch("clients.http.requests.get") as get,
                patch("clients.http.time.sleep"),
            ):
                responses = [
                    make_response(status),
                    make_response(status),
                    make_response(payload={}),
                ]
                get.side_effect = responses
                self.assertEqual(get_json("https://example.test"), {})
                self.assertEqual(get.call_count, 3)
                for response in responses:
                    response.close.assert_called_once()

    @patch("clients.http.time.sleep")
    @patch("clients.http.requests.get")
    def test_429_honors_numeric_retry_after(self, get, sleep):
        get.side_effect = [
            make_response(429, headers={"Retry-After": "7"}),
            make_response(payload={}),
        ]
        self.assertEqual(get_json("https://example.test"), {})
        sleep.assert_called_once_with(7.0)

    def test_invalid_retry_after_uses_backoff(self):
        for header in (None, "tomorrow", "-1", "NaN", "Infinity"):
            with (
                self.subTest(header=header),
                patch("clients.http.requests.get") as get,
                patch("clients.http.time.sleep") as sleep,
            ):
                headers = {} if header is None else {"Retry-After": header}
                get.side_effect = [
                    make_response(429, headers=headers),
                    make_response(payload={}),
                ]
                get_json("https://example.test")
                sleep.assert_called_once_with(1.0)

    def test_exhausted_retries_raise_project_error(self):
        for failure in (requests.exceptions.Timeout("timeout"), 503, 429):
            with (
                self.subTest(failure=failure),
                patch("clients.http.requests.get") as get,
                patch("clients.http.time.sleep"),
            ):
                if isinstance(failure, Exception):
                    get.side_effect = failure
                else:
                    get.side_effect = [make_response(failure) for _ in range(3)]
                with self.assertRaises(ServiceUnavailableError):
                    get_json("https://example.test")
                self.assertEqual(get.call_count, 3)

    @patch("clients.http.requests.get")
    def test_other_library_errors_do_not_escape(self, get):
        get.side_effect = requests.exceptions.HTTPError("foreign error")
        with self.assertRaises(ServiceUnavailableError):
            get_json("https://example.test")

    @patch("clients.http.requests.get")
    def test_non_retryable_status_is_project_error(self, get):
        get.return_value = make_response(404)
        with self.assertRaises(HttpStatusError) as caught:
            get_json("https://example.test")
        self.assertEqual(caught.exception.status_code, 404)
        get.assert_called_once()
        get.return_value.json.assert_not_called()

    @patch("clients.http.time.sleep")
    @patch("clients.http.requests.get")
    def test_body_read_errors_are_retried_and_do_not_escape(self, get, sleep):
        first, second = make_response(), make_response()
        first.json.side_effect = requests.exceptions.ConnectionError("body failed")
        second.json.side_effect = requests.exceptions.Timeout("body timeout")
        get.side_effect = [first, second, make_response(payload={"ok": True})]
        self.assertEqual(get_json("https://example.test"), {"ok": True})
        self.assertEqual(get.call_count, 3)
        self.assertEqual(sleep.call_args_list, [call(1.0), call(2.0)])
        first.close.assert_called_once()
        second.close.assert_called_once()

    @patch("clients.http.requests.get")
    def test_invalid_json_is_project_error(self, get):
        response = make_response()
        response.json.side_effect = requests.exceptions.JSONDecodeError("bad", "x", 0)
        get.return_value = response
        with self.assertRaises(InvalidResponseError):
            get_json("https://example.test")
        response.close.assert_called_once()

    @patch("clients.http.requests.get")
    def test_wrong_json_root_is_rejected(self, get):
        for payload in (None, [], "hello", 123, True):
            with self.subTest(payload=payload):
                get.return_value = make_response(payload=payload)
                with self.assertRaises(InvalidResponseError):
                    get_json("https://example.test")
