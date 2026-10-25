from pathlib import Path

from aviation_tracker.cli import user_interaction
from aviation_tracker.models import Aeroplane
from aviation_tracker.storage import JSONSaver


class FakeAPI:
    def get_aeroplanes(self, country):
        assert country == "France"
        return [
            Aeroplane("LOW", "France", 100, 1000, icao24="1"),
            Aeroplane("HIGH", "France", 200, 9000, icao24="2"),
        ]


def test_user_interaction_happy_path(tmp_path, capsys):
    answers = iter(["France", "1", "France", "0-12000"])

    user_interaction(
        api=FakeAPI(),
        saver=JSONSaver(tmp_path / "planes.json"),
        input_fn=lambda _: next(answers),
    )

    output = capsys.readouterr().out
    assert "Получено самолётов: 2" in output
    assert "HIGH" in output
    assert "LOW" not in output.split("Топ 1 по высоте:")[-1]
    assert (tmp_path / "planes.json").exists()


def test_user_interaction_rejects_empty_country(capsys):
    user_interaction(api=FakeAPI(), saver=JSONSaver(Path("unused.json")), input_fn=lambda _: "")
    assert "не может быть пустым" in capsys.readouterr().out

