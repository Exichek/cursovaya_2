import json

import pytest

from aviation_tracker.models import Aeroplane
from aviation_tracker.storage import JSONSaver


def make_plane(icao24="abc123", altitude=5000):
    return Aeroplane("TEST", "Russia", 200, altitude, icao24=icao24)


def test_add_read_update_and_delete(tmp_path):
    path = tmp_path / "nested" / "planes.json"
    saver = JSONSaver(path)
    plane = make_plane()

    saver.add_aeroplane(plane)
    assert saver.get_aeroplanes() == [plane]

    updated = make_plane(altitude=7000)
    saver.add_aeroplane(updated)
    assert saver.get_aeroplanes()[0].altitude == 7000

    assert saver.delete_aeroplane("abc123") is True
    assert saver.delete_aeroplane("missing") is False
    assert saver.get_aeroplanes() == []


def test_add_many_replace_and_filters(tmp_path):
    saver = JSONSaver(tmp_path / "planes.json")
    planes = [
        make_plane("one", 1000),
        Aeroplane("DE", "Germany", 300, 9000, icao24="two", on_ground=True),
    ]

    saver.add_many(planes, replace=True)

    assert len(saver.get_aeroplanes(min_altitude=5000)) == 1
    assert len(saver.get_aeroplanes(origin_country="germany", on_ground=True)) == 1
    saver.clear()
    assert saver.get_aeroplanes() == []


def test_unknown_criterion_and_bad_object_are_rejected(tmp_path):
    saver = JSONSaver(tmp_path / "planes.json")
    with pytest.raises(ValueError, match="Неизвестные"):
        saver.get_aeroplanes(color="blue")
    with pytest.raises(TypeError):
        saver.add_aeroplane("not a plane")
    with pytest.raises(ValueError):
        saver.delete_aeroplane("")


def test_corrupted_json_has_clear_error(tmp_path):
    path = tmp_path / "planes.json"
    path.write_text("not-json", encoding="utf-8")
    with pytest.raises(ValueError, match="прочитать JSON"):
        JSONSaver(path).get_aeroplanes()


def test_json_is_human_readable_and_unicode(tmp_path):
    path = tmp_path / "planes.json"
    JSONSaver(path).add_aeroplane(make_plane())
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload[0]["origin_country"] == "Russia"

