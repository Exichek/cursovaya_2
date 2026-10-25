"""Консольный интерфейс программы."""

from __future__ import annotations

from collections.abc import Callable

from .api import APIError, AeroplanesAPI
from .models import Aeroplane
from .services import (
    filter_by_altitude,
    filter_by_registration,
    get_top_aeroplanes,
    parse_altitude_range,
)
from .storage import JSONSaver


def _ask_positive_int(prompt: str, input_fn: Callable[[str], str] = input) -> int:
    while True:
        try:
            value = int(input_fn(prompt))
            if value <= 0:
                raise ValueError
            return value
        except ValueError:
            print("Введите положительное целое число.")


def _print_aeroplanes(aeroplanes: list[Aeroplane]) -> None:
    if not aeroplanes:
        print("По заданным условиям самолёты не найдены.")
        return
    for number, aeroplane in enumerate(aeroplanes, start=1):
        print(f"{number}. {aeroplane}")


def user_interaction(
    api: AeroplanesAPI | None = None,
    saver: JSONSaver | None = None,
    input_fn: Callable[[str], str] = input,
) -> None:
    """Запросить параметры, получить, сохранить и вывести данные."""
    api = api or AeroplanesAPI()
    saver = saver or JSONSaver()

    country = input_fn("Введите название страны: ").strip()
    if not country:
        print("Название страны не может быть пустым.")
        return
    try:
        aeroplanes = api.get_aeroplanes(country)
    except (APIError, ValueError) as exc:
        print(f"Не удалось получить данные: {exc}")
        return

    saver.add_many(aeroplanes, replace=True)
    print(f"Получено самолётов: {len(aeroplanes)}")
    print(f"Данные сохранены в {saver.path}")
    if not aeroplanes:
        print("Сейчас OpenSky не видит самолётов в выбранной области.")
        return

    top_n = _ask_positive_int(
        "Введите количество самолётов для топа по высоте: ", input_fn
    )
    registration = input_fn(
        "Страны регистрации через запятую (Enter — без фильтра): "
    )
    selected = filter_by_registration(aeroplanes, registration.split(","))

    while True:
        altitude_text = input_fn(
            "Диапазон высоты в метрах, например 1000-12000 (Enter — любой): "
        )
        try:
            minimum, maximum = parse_altitude_range(altitude_text)
            break
        except ValueError as exc:
            print(exc)
    if minimum is not None or maximum is not None:
        selected = filter_by_altitude(selected, minimum, maximum)

    print(f"\nТоп {top_n} по высоте:")
    _print_aeroplanes(get_top_aeroplanes(selected, top_n))

