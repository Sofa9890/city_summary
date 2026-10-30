"""Ошибки приложения: вызывающий код не зависит от исключений requests."""


class CitySummaryError(Exception):
    exit_code = 4


class InputError(CitySummaryError):
    exit_code = 2


class CityNotFoundError(CitySummaryError):
    exit_code = 3


class CurrencyNotFoundError(CitySummaryError):
    exit_code = 3


class ServiceUnavailableError(CitySummaryError):
    pass


class InvalidResponseError(CitySummaryError):
    pass


class HttpStatusError(CitySummaryError):
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"Внешний сервис вернул HTTP {status_code}.")
