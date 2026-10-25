"""Предметные модели приложения."""

from __future__ import annotations

from functools import total_ordering
from typing import Any, Iterable


class ValidationError(ValueError):
    """Переданы некорректные данные самолёта."""


@total_ordering
class Aeroplane:
    """Самолёт и его последнее состояние, полученное от OpenSky.

    Атрибуты закрыты от прямого изменения. Сравнение операторами ``<`` и ``>``
    выполняется по высоте. Для явного сравнения скорости предусмотрен метод
    :meth:`compare_speed`.
    """

    def __init__(
        self,
        callsign: str,
        origin_country: str,
        velocity: float | int | None,
        altitude: float | int | None,
        *,
        icao24: str = "unknown",
        longitude: float | int | None = None,
        latitude: float | int | None = None,
        on_ground: bool = False,
        vertical_rate: float | int | None = None,
    ) -> None:
        self._callsign = self._validate_text(callsign, "Позывной", "Неизвестен")
        self._origin_country = self._validate_text(
            origin_country, "Страна регистрации", "Неизвестна"
        )
        self._icao24 = self._validate_text(icao24, "ICAO24", "unknown").lower()
        self._velocity = self._validate_number(
            velocity, "Скорость", minimum=0.0, allow_none=True
        )
        self._altitude = self._validate_number(
            altitude, "Высота", minimum=-1000.0, allow_none=True
        )
        self._longitude = self._validate_number(
            longitude, "Долгота", minimum=-180.0, maximum=180.0, allow_none=True
        )
        self._latitude = self._validate_number(
            latitude, "Широта", minimum=-90.0, maximum=90.0, allow_none=True
        )
        if not isinstance(on_ground, bool):
            raise ValidationError("Признак нахождения на земле должен быть bool")
        self._on_ground = on_ground
        self._vertical_rate = self._validate_number(
            vertical_rate, "Вертикальная скорость", allow_none=True
        )

    @staticmethod
    def _validate_text(value: Any, name: str, default: str) -> str:
        if value is None or (isinstance(value, str) and not value.strip()):
            return default
        if not isinstance(value, str):
            raise ValidationError(f"{name} должен быть строкой")
        return value.strip()

    @staticmethod
    def _validate_number(
        value: Any,
        name: str,
        *,
        minimum: float | None = None,
        maximum: float | None = None,
        allow_none: bool = False,
    ) -> float | None:
        if value is None and allow_none:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValidationError(f"{name} должна быть числом")
        result = float(value)
        if minimum is not None and result < minimum:
            raise ValidationError(f"{name} не может быть меньше {minimum}")
        if maximum is not None and result > maximum:
            raise ValidationError(f"{name} не может быть больше {maximum}")
        return result

    @property
    def callsign(self) -> str:
        return self._callsign

    @property
    def origin_country(self) -> str:
        return self._origin_country

    @property
    def icao24(self) -> str:
        return self._icao24

    @property
    def velocity(self) -> float | None:
        """Горизонтальная скорость в метрах в секунду."""
        return self._velocity

    @property
    def altitude(self) -> float | None:
        """Барометрическая (или геометрическая) высота в метрах."""
        return self._altitude

    @property
    def longitude(self) -> float | None:
        return self._longitude

    @property
    def latitude(self) -> float | None:
        return self._latitude

    @property
    def on_ground(self) -> bool:
        return self._on_ground

    @property
    def vertical_rate(self) -> float | None:
        return self._vertical_rate

    @property
    def comparable_altitude(self) -> float:
        """Высота для сортировки: неизвестные значения идут в конец."""
        return self.altitude if self.altitude is not None else float("-inf")

    @property
    def comparable_velocity(self) -> float:
        return self.velocity if self.velocity is not None else float("-inf")

    def compare_altitude(self, other: Aeroplane) -> int:
        """Вернуть -1, 0 или 1 после сравнения высоты двух самолётов."""
        self._ensure_aeroplane(other)
        return (self.comparable_altitude > other.comparable_altitude) - (
            self.comparable_altitude < other.comparable_altitude
        )

    def compare_speed(self, other: Aeroplane) -> int:
        """Вернуть -1, 0 или 1 после сравнения скорости двух самолётов."""
        self._ensure_aeroplane(other)
        return (self.comparable_velocity > other.comparable_velocity) - (
            self.comparable_velocity < other.comparable_velocity
        )

    @staticmethod
    def _ensure_aeroplane(other: object) -> None:
        if not isinstance(other, Aeroplane):
            raise TypeError("Сравнивать можно только объекты Aeroplane")

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Aeroplane):
            return NotImplemented
        return self.comparable_altitude < other.comparable_altitude

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Aeroplane):
            return NotImplemented
        return (
            self.icao24 == other.icao24
            and self.callsign == other.callsign
            and self.origin_country == other.origin_country
            and self.velocity == other.velocity
            and self.altitude == other.altitude
        )

    def __repr__(self) -> str:
        return (
            f"Aeroplane(callsign={self.callsign!r}, "
            f"country={self.origin_country!r}, altitude={self.altitude!r}, "
            f"velocity={self.velocity!r})"
        )

    def __str__(self) -> str:
        altitude = f"{self.altitude:.0f} м" if self.altitude is not None else "нет данных"
        velocity = (
            f"{self.velocity:.1f} м/с" if self.velocity is not None else "нет данных"
        )
        status = "на земле" if self.on_ground else "в полёте"
        return (
            f"{self.callsign} [{self.icao24}] — {self.origin_country}; "
            f"высота: {altitude}; скорость: {velocity}; {status}"
        )

    def to_dict(self) -> dict[str, Any]:
        """Преобразовать объект в JSON-совместимый словарь."""
        return {
            "icao24": self.icao24,
            "callsign": self.callsign,
            "origin_country": self.origin_country,
            "velocity": self.velocity,
            "altitude": self.altitude,
            "longitude": self.longitude,
            "latitude": self.latitude,
            "on_ground": self.on_ground,
            "vertical_rate": self.vertical_rate,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Aeroplane:
        return cls(
            callsign=data.get("callsign"),
            origin_country=data.get("origin_country"),
            velocity=data.get("velocity"),
            altitude=data.get("altitude"),
            icao24=data.get("icao24", "unknown"),
            longitude=data.get("longitude"),
            latitude=data.get("latitude"),
            on_ground=data.get("on_ground", False),
            vertical_rate=data.get("vertical_rate"),
        )

    @classmethod
    def from_state_vector(cls, state: list[Any]) -> Aeroplane:
        """Создать объект из массива ``states`` ответа OpenSky."""
        if not isinstance(state, list) or len(state) < 13:
            raise ValidationError("Некорректный вектор состояния OpenSky")
        altitude = state[7] if state[7] is not None else (
            state[13] if len(state) > 13 else None
        )
        return cls(
            icao24=state[0],
            callsign=state[1],
            origin_country=state[2],
            longitude=state[5],
            latitude=state[6],
            altitude=altitude,
            on_ground=state[8],
            velocity=state[9],
            vertical_rate=state[11],
        )

    @classmethod
    def cast_to_object_list(cls, states: Iterable[list[Any]]) -> list[Aeroplane]:
        """Преобразовать набор векторов OpenSky в список объектов."""
        aeroplanes: list[Aeroplane] = []
        for state in states:
            try:
                aeroplanes.append(cls.from_state_vector(state))
            except (ValidationError, TypeError, IndexError):
                continue
        return aeroplanes

