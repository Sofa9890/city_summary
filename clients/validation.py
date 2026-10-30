"""Проверки данных на границе внешнего API."""

import math

from exceptions import InvalidResponseError


def require_number(value: object, field: str) -> float:
    # bool — подкласс int, но True не является допустимой температурой или курсом.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidResponseError(f"Поле {field} должно содержать число.")
    try:
        number = float(value)
    except (ValueError, OverflowError) as exc:
        raise InvalidResponseError(f"Некорректное число в поле {field}.") from exc
    if not math.isfinite(number):
        raise InvalidResponseError(f"Поле {field} должно содержать конечное число.")
    return number
