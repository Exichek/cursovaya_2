from unittest.mock import Mock

import pytest
import requests

from aviation_tracker.api import APIError, AeroplanesAPI, BoundingBox, CountryNotFoundError


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


def test_get_country_bounds_uses_nominatim_response():
    session = Mock()
    session.get.return_value = FakeResponse(
        [{"boundingbox": ["41.1", "81.8", "19.6", "180.0"]}]
    )
    api = AeroplanesAPI(session=session)

    bounds = api.get_country_bounds("Russia")

    assert bounds == BoundingBox(41.1, 81.8, 19.6, 180.0)
    assert session.get.call_args.kwargs["params"]["country"] == "Russia"


def test_country_not_found():
    session = Mock()
    session.get.return_value = FakeResponse([])
    with pytest.raises(CountryNotFoundError):
        AeroplanesAPI(session=session).get_country_bounds("Atlantis")


def test_get_aeroplanes_calls_both_services():
    session = Mock()
    state = ["abc", "TEST", "France", 1, 2, 2, 48, 8000, False, 220, 0, 1, None]
    session.get.side_effect = [
        FakeResponse([{"boundingbox": ["41", "51", "-5", "9"]}]),
        FakeResponse({"time": 1, "states": [state]}),
    ]

    result = AeroplanesAPI(session=session).get_aeroplanes("France")

    assert len(result) == 1
    assert result[0].callsign == "TEST"
    assert session.get.call_args.kwargs["params"] == {
        "lamin": 41.0,
        "lamax": 51.0,
        "lomin": -5.0,
        "lomax": 9.0,
    }


def test_oauth_token_is_requested_and_reused():
    session = Mock()
    session.post.return_value = FakeResponse({"access_token": "secret", "expires_in": 1800})
    api = AeroplanesAPI(session=session, client_id="id", client_secret="secret")

    first = api._authorization_headers()
    second = api._authorization_headers()

    assert first == second == {"Authorization": "Bearer secret"}
    session.post.assert_called_once()


def test_only_one_oauth_value_is_configuration_error():
    api = AeroplanesAPI(session=Mock(), client_id="id", client_secret=None)
    api._client_secret = None
    with pytest.raises(APIError, match="обе переменные"):
        api._authorization_headers()


@pytest.mark.parametrize(
    ("status", "message"), [(401, "авторизации"), (429, "лимит"), (500, "HTTP 500")]
)
def test_http_errors_are_explained(status, message):
    session = Mock()
    session.get.return_value = FakeResponse({}, status)
    api = AeroplanesAPI(session=session)
    with pytest.raises(APIError, match=message):
        api._get_json("https://example.test", params={}, headers={}, service="Test")


def test_timeout_is_explained():
    session = Mock()
    session.get.side_effect = requests.Timeout()
    with pytest.raises(APIError, match="не ответил"):
        AeroplanesAPI(session=session)._get_json(
            "https://example.test", params={}, headers={}, service="Test"
        )


def test_non_json_response_is_explained():
    session = Mock()
    session.get.return_value = FakeResponse(ValueError("bad json"))
    with pytest.raises(APIError, match="не JSON"):
        AeroplanesAPI(session=session)._get_json(
            "https://example.test", params={}, headers={}, service="Test"
        )

