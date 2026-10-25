"""Абстракция хранилища и реализация для JSON-файла."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterable

from .models import Aeroplane, ValidationError


class AbstractSaver(ABC):
    """Интерфейс коннектора к хранилищу самолётов."""

    @abstractmethod
    def add_aeroplane(self, aeroplane: Aeroplane) -> None:
        """Добавить или обновить самолёт."""

    @abstractmethod
    def get_aeroplanes(self, **criteria: Any) -> list[Aeroplane]:
        """Получить самолёты по указанным критериям."""

    @abstractmethod
    def delete_aeroplane(self, aeroplane: Aeroplane | str) -> bool:
        """Удалить самолёт; вернуть признак успешного удаления."""

    @abstractmethod
    def clear(self) -> None:
        """Удалить все записи из хранилища."""


class JSONSaver(AbstractSaver):
    """Хранит список самолётов в читаемом JSON-файле."""

    SUPPORTED_CRITERIA = {
        "icao24",
        "callsign",
        "origin_country",
        "on_ground",
        "min_altitude",
        "max_altitude",
        "min_velocity",
        "max_velocity",
    }

    def __init__(self, filename: str | Path = "data/aeroplanes.json") -> None:
        self._path = Path(filename)

    @property
    def path(self) -> Path:
        return self._path

    def add_aeroplane(self, aeroplane: Aeroplane) -> None:
        if not isinstance(aeroplane, Aeroplane):
            raise TypeError("Можно сохранять только объекты Aeroplane")
        aeroplanes = self._read()
        for index, saved in enumerate(aeroplanes):
            if saved.icao24 == aeroplane.icao24:
                aeroplanes[index] = aeroplane
                break
        else:
            aeroplanes.append(aeroplane)
        self._write(aeroplanes)

    def add_many(self, aeroplanes: Iterable[Aeroplane], *, replace: bool = False) -> None:
        """Сохранить коллекцию за одну операцию записи."""
        result = [] if replace else self._read()
        by_icao = {aeroplane.icao24: aeroplane for aeroplane in result}
        for aeroplane in aeroplanes:
            if not isinstance(aeroplane, Aeroplane):
                raise TypeError("Можно сохранять только объекты Aeroplane")
            by_icao[aeroplane.icao24] = aeroplane
        self._write(by_icao.values())

    def get_aeroplanes(self, **criteria: Any) -> list[Aeroplane]:
        unknown = set(criteria) - self.SUPPORTED_CRITERIA
        if unknown:
            raise ValueError(f"Неизвестные критерии: {', '.join(sorted(unknown))}")
        result = self._read()
        exact = ("icao24", "callsign", "origin_country", "on_ground")
        for name in exact:
            if name in criteria:
                expected = criteria[name]
                if isinstance(expected, str):
                    result = [
                        item
                        for item in result
                        if str(getattr(item, name)).casefold() == expected.casefold()
                    ]
                else:
                    result = [item for item in result if getattr(item, name) == expected]

        ranges = (
            ("min_altitude", "altitude", lambda value, limit: value >= limit),
            ("max_altitude", "altitude", lambda value, limit: value <= limit),
            ("min_velocity", "velocity", lambda value, limit: value >= limit),
            ("max_velocity", "velocity", lambda value, limit: value <= limit),
        )
        for criterion, attribute, check in ranges:
            if criterion in criteria:
                limit = float(criteria[criterion])
                result = [
                    item
                    for item in result
                    if (value := getattr(item, attribute)) is not None
                    and check(value, limit)
                ]
        return result

    def delete_aeroplane(self, aeroplane: Aeroplane | str) -> bool:
        icao24 = aeroplane.icao24 if isinstance(aeroplane, Aeroplane) else aeroplane
        if not isinstance(icao24, str) or not icao24.strip():
            raise ValueError("Нужен объект Aeroplane или непустой ICAO24")
        current = self._read()
        filtered = [item for item in current if item.icao24 != icao24.lower()]
        if len(filtered) == len(current):
            return False
        self._write(filtered)
        return True

    def clear(self) -> None:
        self._write([])

    def _read(self) -> list[Aeroplane]:
        if not self.path.exists():
            return []
        try:
            with self.path.open("r", encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Не удалось прочитать JSON-файл {self.path}: {exc}") from exc
        if not isinstance(payload, list):
            raise ValueError("Корнем JSON-файла должен быть список")
        try:
            return [Aeroplane.from_dict(item) for item in payload]
        except (TypeError, ValidationError) as exc:
            raise ValueError(f"В JSON-файле есть некорректная запись: {exc}") from exc

    def _write(self, aeroplanes: Iterable[Aeroplane]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with temporary.open("w", encoding="utf-8") as file:
                json.dump(
                    [item.to_dict() for item in aeroplanes],
                    file,
                    ensure_ascii=False,
                    indent=2,
                )
            temporary.replace(self.path)
        except OSError as exc:
            raise ValueError(f"Не удалось записать JSON-файл {self.path}: {exc}") from exc

