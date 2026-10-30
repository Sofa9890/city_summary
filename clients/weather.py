from typing import Any

from clients.http import get_json
from clients.validation import require_number
from exceptions import CityNotFoundError, InputError, InvalidResponseError

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_DESCRIPTIONS = {
    0: "ясно",
    1: "преимущественно ясно",
    2: "переменная облачность",
    3: "пасмурно",
    45: "туман",
    48: "изморозевый туман",
    51: "слабая морось",
    53: "морось",
    55: "сильная морось",
    56: "слабая переохлаждённая морось",
    57: "сильная переохлаждённая морось",
    61: "слабый дождь",
    63: "дождь",
    65: "сильный дождь",
    66: "слабый переохлаждённый дождь",
    67: "сильный переохлаждённый дождь",
    71: "слабый снег",
    73: "снег",
    75: "сильный снег",
    77: "снежные зёрна",
    80: "слабый ливень",
    81: "ливень",
    82: "сильный ливень",
    85: "слабый снежный ливень",
    86: "сильный снежный ливень",
    95: "гроза",
    96: "гроза с небольшим градом",
    99: "гроза с сильным градом",
}


def get_weather(city: str) -> dict[str, Any]:
    city = city.strip()
    if not city:
        raise InputError("Название города не должно быть пустым.")

    geocoding = get_json(
        GEOCODING_URL,
        params={"name": city, "count": 1, "language": "en", "format": "json"},
    )
    if geocoding.get("error"):
        raise InvalidResponseError("Геокодер сообщил об ошибке в ответе.")
    results = geocoding.get("results", [])
    if not isinstance(results, list):
        raise InvalidResponseError("Геокодер вернул некорректный список городов.")
    if not results:
        raise CityNotFoundError(f"Город «{city}» не найден.")
    location = results[0]
    if not isinstance(location, dict):
        raise InvalidResponseError("Геокодер вернул некорректные данные города.")
    latitude = require_number(location.get("latitude"), "latitude")
    longitude = require_number(location.get("longitude"), "longitude")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise InvalidResponseError(
            "Координаты города находятся вне допустимого диапазона."
        )

    forecast = get_json(
        WEATHER_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,weather_code",
            "temperature_unit": "celsius",
        },
    )
    current = forecast.get("current")
    if not isinstance(current, dict):
        raise InvalidResponseError("В ответе погоды отсутствует объект current.")
    temperature = require_number(current.get("temperature_2m"), "temperature_2m")
    code = current.get("weather_code")
    if (
        isinstance(code, bool)
        or not isinstance(code, int)
        or code not in WEATHER_DESCRIPTIONS
    ):
        raise InvalidResponseError("Сервис погоды вернул неизвестный weather_code.")
    return {"temp_c": temperature, "description": WEATHER_DESCRIPTIONS[code]}
