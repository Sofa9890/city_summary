"""Общий GET: статус, timeout, retry и JSON обрабатываются здесь."""

import math
import time
from typing import Any

import requests

from exceptions import (
    HttpStatusError,
    InvalidResponseError,
    ServiceUnavailableError,
)

TIMEOUT_SECONDS = 8
MAX_ATTEMPTS = 3  # Первая попытка и два повтора.
RETRYABLE_STATUSES = {500, 502, 503, 504, 429}


def _retry_delay(retry_after: str | None, attempt: int) -> float:
    if retry_after is not None:
        try:
            seconds = float(retry_after)
        except ValueError:
            pass
        else:
            if math.isfinite(seconds) and seconds >= 0:
                return seconds
    return float(attempt)


def get_json(
    url: str,
    params: dict[str, str | int | float] | None = None,
) -> dict[str, Any]:
    """Вернуть JSON-объект либо возбудить собственную ошибку проекта."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = None
        try:
            response = requests.get(
                url,
                params=params,
                timeout=TIMEOUT_SECONDS,
                headers={"Accept": "application/json"},
                allow_redirects=False,
                stream=True,  # Проверяем статус до чтения тела ответа.
            )
            status = response.status_code
            if status in RETRYABLE_STATUSES:
                if attempt == MAX_ATTEMPTS:
                    raise ServiceUnavailableError(
                        f"Сервис недоступен после трёх попыток: HTTP {status}."
                    )
                retry_after = (
                    response.headers.get("Retry-After") if status == 429 else None
                )
                delay = _retry_delay(retry_after, attempt)
            elif not 200 <= status < 300:
                raise HttpStatusError(status)
            else:
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise InvalidResponseError(
                        "Сервис вернул некорректный JSON."
                    ) from exc
                if not isinstance(payload, dict):
                    raise InvalidResponseError(
                        "Ожидался JSON-объект, получен другой тип."
                    )
                return payload
        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
        ) as exc:
            if attempt == MAX_ATTEMPTS:
                raise ServiceUnavailableError(
                    "Сервис недоступен после трёх попыток: таймаут или ошибка соединения."
                ) from exc
            delay = float(attempt)
        except requests.exceptions.RequestException as exc:
            raise ServiceUnavailableError("Не удалось выполнить HTTP-запрос.") from exc
        finally:
            if response is not None:
                response.close()

        time.sleep(delay)

    raise ServiceUnavailableError("Лимит попыток запроса исчерпан.")
