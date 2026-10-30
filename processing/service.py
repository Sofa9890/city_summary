from typing import Any

from clients.rates import get_rate, normalize_currency
from clients.weather import get_weather
from exceptions import InputError
from processing.preprocessing import is_expensive, needs_warm_clothes


def build_city_summary(city: str, currency: str = "USD") -> dict[str, Any]:
    city = city.strip()
    if not city:
        raise InputError("Название города не должно быть пустым.")
    currency = normalize_currency(currency)
    rate = get_rate(currency)
    weather = get_weather(city)
    return {
        "city": city,
        "weather": {
            **weather,
            "warm_clothes": needs_warm_clothes(weather["temp_c"]),
        },
        "rates": {
            "currency": currency,
            "rate_to_rub": rate,
            "expensive": is_expensive(rate),
        },
    }
