import pytest

from aviation_tracker.models import Aeroplane
from aviation_tracker.services import (
    filter_by_altitude,
    filter_by_registration,
    get_top_aeroplanes,
    parse_altitude_range,
)


@pytest.fixture
def planes():
    return [
        Aeroplane("ONE", "Russia", 100, 1000, icao24="1"),
        Aeroplane("TWO", "Germany", 200, 9000, icao24="2"),
        Aeroplane("THREE", "Russia", None, None, icao24="3"),
    ]


def test_filter_by_registration_is_case_insensitive(planes):
    result = filter_by_registration(planes, ["rUSSIA"])
    assert [plane.callsign for plane in result] == ["ONE", "THREE"]
    assert filter_by_registration(planes, []) == planes


def test_filter_by_altitude(planes):
    assert [p.callsign for p in filter_by_altitude(planes, 500, 5000)] == ["ONE"]
    with pytest.raises(ValueError):
        filter_by_altitude(planes, 5000, 1000)


def test_top_n_is_sorted_descending(planes):
    assert [p.callsign for p in get_top_aeroplanes(planes, 2)] == ["TWO", "ONE"]
    with pytest.raises(ValueError):
        get_top_aeroplanes(planes, 0)


@pytest.mark.parametrize(
    ("text", "expected"),
    [("", (None, None)), ("1000 - 12000", (1000.0, 12000.0))],
)
def test_parse_altitude_range(text, expected):
    assert parse_altitude_range(text) == expected


@pytest.mark.parametrize("text", ["1000", "high-low", "5000-1000"])
def test_parse_altitude_range_rejects_bad_input(text):
    with pytest.raises(ValueError):
        parse_altitude_range(text)

