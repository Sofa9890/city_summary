import argparse
import json
import sys
from typing import Any

from exceptions import CitySummaryError
from processing.service import build_city_summary


def format_summary(summary: dict[str, Any]) -> str:
    weather = summary["weather"]
    rates = summary["rates"]
    warm = "да" if weather["warm_clothes"] else "нет"
    expensive = "да" if rates["expensive"] else "нет"
    return "\n".join(
        [
            f"Город: {summary['city']}",
            f"Погода: {weather['temp_c']:.1f}°C, {weather['description']}",
            f"Тёплая одежда: {warm}",
            f"{rates['currency']}→RUB: {rates['rate_to_rub']:.2f}",
            f"Дорогой курс: {expensive}",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Погода в городе и курс валюты к рублю."
    )
    parser.add_argument("--city", required=True, help="Город, например Moscow")
    parser.add_argument(
        "--currency", default="USD", help="Код валюты, например USD или EUR"
    )
    parser.add_argument(
        "--json", action="store_true", help="Вывести сводку в формате JSON"
    )
    args = parser.parse_args(argv)

    try:
        summary = build_city_summary(args.city, args.currency)
    except CitySummaryError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return exc.exit_code

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
    else:
        print(format_summary(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
