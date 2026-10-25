"""Независимые функции фильтрации и сортировки."""

from __future__ import annotations

from collections.abc import Iterable

from .models import Aeroplane


def filter_by_registration(
    aeroplanes: Iterable[Aeroplane], countries: Iterable[str]
) -> list[Aeroplane]:
    """Отфильтровать самолёты по одной или нескольким странам регистрации."""
    normalized = {country.strip().casefold() for country in countries if country.strip()}
    if not normalized:
        return list(aeroplanes)
    return [
        plane for plane in aeroplanes if plane.origin_country.casefold() in normalized
    ]


def filter_by_altitude(
    aeroplanes: Iterable[Aeroplane],
    minimum: float | None = None,
    maximum: float | None = None,
) -> list[Aeroplane]:
    """Оставить самолёты с известной высотой внутри диапазона."""
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError("Минимальная высота не может быть больше максимальной")
    return [
        plane
        for plane in aeroplanes
        if plane.altitude is not None
        and (minimum is None or plane.altitude >= minimum)
        and (maximum is None or plane.altitude <= maximum)
    ]


def sort_by_altitude(
    aeroplanes: Iterable[Aeroplane], *, descending: bool = True
) -> list[Aeroplane]:
    return sorted(
        aeroplanes, key=lambda plane: plane.comparable_altitude, reverse=descending
    )


def get_top_aeroplanes(
    aeroplanes: Iterable[Aeroplane], count: int
) -> list[Aeroplane]:
    """Вернуть топ N самолётов по высоте (DESC)."""
    if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
        raise ValueError("Количество самолётов должно быть положительным целым числом")
    return sort_by_altitude(aeroplanes)[:count]


def parse_altitude_range(value: str) -> tuple[float | None, float | None]:
    """Разобрать строку вида ``1000-12000``; пустая строка означает без фильтра."""
    cleaned = value.strip()
    if not cleaned:
        return None, None
    parts = cleaned.replace(" ", "").split("-")
    if len(parts) != 2 or not all(parts):
        raise ValueError("Диапазон нужно ввести в формате 1000-12000")
    try:
        minimum, maximum = map(float, parts)
    except ValueError as exc:
        raise ValueError("Границы высоты должны быть числами") from exc
    if minimum > maximum:
        raise ValueError("Минимальная высота не может быть больше максимальной")
    return minimum, maximum

