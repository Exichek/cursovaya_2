"""Получение координат стран и состояний самолётов через HTTP API."""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import requests

from .models import Aeroplane


class APIError(RuntimeError):
    """Ошибка внешнего API или некорректный ответ сервиса."""


class CountryNotFoundError(APIError):
    """Nominatim не нашёл указанную страну."""


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Границы области: юг, север, запад, восток."""

    south: float
    north: float
    west: float
    east: float

    def as_opensky_params(self) -> dict[str, float]:
        return {
            "lamin": self.south,
            "lamax": self.north,
            "lomin": self.west,
            "lomax": self.east,
        }


class AbstractAeroplanesAPI(ABC):
    """Интерфейс источника сведений о воздушном пространстве."""

    @abstractmethod
    def get_country_bounds(self, country: str) -> BoundingBox:
        """Получить географические границы страны."""

    @abstractmethod
    def get_aeroplanes(self, country: str) -> list[Aeroplane]:
        """Получить самолёты в границах выбранной страны."""


class AeroplanesAPI(AbstractAeroplanesAPI):
    """Клиент Nominatim + OpenSky с необязательной OAuth2-авторизацией."""

    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    OPENSKY_STATES_URL = "https://opensky-network.org/api/states/all"
    OPENSKY_TOKEN_URL = (
        "https://auth.opensky-network.org/auth/realms/opensky-network/"
        "protocol/openid-connect/token"
    )

    def __init__(
        self,
        session: requests.Session | None = None,
        *,
        timeout: float = 20.0,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        self._session = session or requests.Session()
        self._timeout = timeout
        self._client_id = client_id or os.getenv("OPENSKY_CLIENT_ID")
        self._client_secret = client_secret or os.getenv("OPENSKY_CLIENT_SECRET")
        self._access_token: str | None = None
        self._token_expires_at = 0.0

    def get_country_bounds(self, country: str) -> BoundingBox:
        if not isinstance(country, str) or not country.strip():
            raise ValueError("Название страны не может быть пустым")

        headers = {
            "User-Agent": os.getenv(
                "NOMINATIM_USER_AGENT", "airspace-course-project/1.0"
            )
        }
        params: dict[str, Any] = {
            "country": country.strip(),
            "format": "jsonv2",
            "limit": 1,
            "addressdetails": 1,
        }
        email = os.getenv("NOMINATIM_EMAIL")
        if email:
            params["email"] = email

        payload = self._get_json(
            self.NOMINATIM_URL, params=params, headers=headers, service="Nominatim"
        )
        if not isinstance(payload, list) or not payload:
            raise CountryNotFoundError(f"Страна «{country.strip()}» не найдена")
        try:
            south, north, west, east = map(float, payload[0]["boundingbox"])
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise APIError("Nominatim вернул ответ без корректного boundingbox") from exc
        return BoundingBox(south=south, north=north, west=west, east=east)

    def get_aeroplanes(self, country: str) -> list[Aeroplane]:
        bounds = self.get_country_bounds(country)
        headers = self._authorization_headers()
        payload = self._get_json(
            self.OPENSKY_STATES_URL,
            params=bounds.as_opensky_params(),
            headers=headers,
            service="OpenSky",
        )
        if not isinstance(payload, dict):
            raise APIError("OpenSky вернул ответ неизвестного формата")
        states = payload.get("states") or []
        if not isinstance(states, list):
            raise APIError("Поле states в ответе OpenSky имеет неверный формат")
        return Aeroplane.cast_to_object_list(states)

    def _authorization_headers(self) -> dict[str, str]:
        if not self._client_id and not self._client_secret:
            return {}
        if not self._client_id or not self._client_secret:
            raise APIError(
                "Для OpenSky нужно задать обе переменные: "
                "OPENSKY_CLIENT_ID и OPENSKY_CLIENT_SECRET"
            )
        return {"Authorization": f"Bearer {self._get_access_token()}"}

    def _get_access_token(self) -> str:
        if self._access_token and time.monotonic() < self._token_expires_at:
            return self._access_token
        try:
            response = self._session.post(
                self.OPENSKY_TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
            payload = response.json()
            token = payload["access_token"]
            expires_in = int(payload.get("expires_in", 1800))
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            raise APIError(f"Не удалось авторизоваться в OpenSky: {exc}") from exc
        self._access_token = str(token)
        self._token_expires_at = time.monotonic() + max(expires_in - 60, 1)
        return self._access_token

    def _get_json(
        self,
        url: str,
        *,
        params: dict[str, Any],
        headers: dict[str, str],
        service: str,
    ) -> Any:
        try:
            response = self._session.get(
                url, params=params, headers=headers, timeout=self._timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.Timeout as exc:
            raise APIError(f"{service} не ответил за {self._timeout:g} секунд") from exc
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "?"
            if status == 429:
                message = f"{service}: исчерпан лимит запросов (HTTP 429)"
            elif status == 401:
                message = f"{service}: ошибка авторизации (HTTP 401)"
            else:
                message = f"{service} вернул ошибку HTTP {status}"
            raise APIError(message) from exc
        except requests.RequestException as exc:
            raise APIError(f"Не удалось подключиться к {service}: {exc}") from exc
        except ValueError as exc:
            raise APIError(f"{service} вернул не JSON") from exc

