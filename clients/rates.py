import re

from clients.http import get_json
from clients.validation import require_number
from exceptions import (
    CurrencyNotFoundError,
    HttpStatusError,
    InputError,
    InvalidResponseError,
)

RATE_URL = "https://api.frankfurter.dev/v2/rate/{currency}/RUB"


def normalize_currency(currency: str) -> str:
    currency = currency.strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", currency):
        raise InputError(
            "Код валюты должен состоять из трёх латинских букв, например USD."
        )
    return currency


def get_rate(currency: str) -> float:
    currency = normalize_currency(currency)
    try:
        payload = get_json(RATE_URL.format(currency=currency))
    except HttpStatusError as exc:
        if exc.status_code in {400, 404, 422}:
            raise CurrencyNotFoundError(
                f"Валюта {currency} или её курс к RUB не найдены."
            ) from exc
        raise

    if payload.get("base") != currency or payload.get("quote") != "RUB":
        raise InvalidResponseError("В ответе курса указана другая валютная пара.")
    rate = require_number(payload.get("rate"), "rate")
    if rate <= 0:
        raise InvalidResponseError("Курс валюты должен быть положительным.")
    return rate
