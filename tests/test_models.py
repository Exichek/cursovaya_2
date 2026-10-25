import pytest

from aviation_tracker.models import Aeroplane, ValidationError


def make_plane(**overrides):
    values = {
        "callsign": "AFL100",
        "origin_country": "Russia",
        "velocity": 250,
        "altitude": 10_000,
        "icao24": "ABC123",
    }
    values.update(overrides)
    return Aeroplane(**values)


def test_aeroplane_properties_and_string():
    plane = make_plane()

    assert plane.callsign == "AFL100"
    assert plane.icao24 == "abc123"
    assert plane.velocity == 250.0
    assert "10000 м" in str(plane)
    assert "AFL100" in repr(plane)


def test_empty_api_text_is_replaced_with_readable_defaults():
    plane = make_plane(callsign="  ", origin_country=None)

    assert plane.callsign == "Неизвестен"
    assert plane.origin_country == "Неизвестна"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("velocity", -1),
        ("velocity", "fast"),
        ("altitude", -1001),
        ("longitude", 181),
        ("latitude", -91),
        ("on_ground", 1),
    ],
)
def test_validation_rejects_invalid_values(field, value):
    with pytest.raises(ValidationError):
        make_plane(**{field: value})


def test_comparison_by_altitude_and_speed():
    low = make_plane(icao24="low", altitude=1000, velocity=300)
    high = make_plane(icao24="high", altitude=9000, velocity=200)

    assert low < high
    assert high.compare_altitude(low) == 1
    assert low.compare_speed(high) == 1
    with pytest.raises(TypeError):
        low.compare_speed("not a plane")


def test_unknown_altitude_is_sorted_below_known_altitude():
    unknown = make_plane(icao24="none", altitude=None)
    known = make_plane(icao24="known", altitude=0)

    assert unknown < known


def test_state_vector_conversion_and_round_trip():
    state = [
        "abc123",
        " TEST1 ",
        "Germany",
        1,
        2,
        13.4,
        52.5,
        None,
        False,
        210.5,
        90,
        4.2,
        None,
        11_000,
    ]

    plane = Aeroplane.from_state_vector(state)
    restored = Aeroplane.from_dict(plane.to_dict())

    assert plane.callsign == "TEST1"
    assert plane.altitude == 11_000
    assert restored == plane


def test_cast_to_object_list_skips_broken_vectors():
    valid = ["abc", "OK", "France", 1, 2, 2, 48, 5000, False, 100, 1, 0, None]

    result = Aeroplane.cast_to_object_list([valid, ["too", "short"]])

    assert len(result) == 1
    assert result[0].callsign == "OK"


def test_state_vector_must_have_required_fields():
    with pytest.raises(ValidationError):
        Aeroplane.from_state_vector([1, 2])

