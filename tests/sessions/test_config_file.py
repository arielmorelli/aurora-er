from pathlib import Path

import yaml

from aurora_er.sessions.config_file import config_from_yaml, config_to_yaml
from tests.small_inputs import small_config


def test_round_trips_every_value() -> None:
    folder = Path("/sessions/20261004T153012.123456Z")
    config = small_config(folder)
    assert config_from_yaml(config_to_yaml(config, folder), folder) == config


def test_stores_paths_relative_to_the_session() -> None:
    folder = Path("/sessions/s1")
    document = yaml.safe_load(config_to_yaml(small_config(folder), folder))
    assert document["battery"]["file"] == "battery.xlsx"
    assert {market["file"] for market in document["markets"]} == {"prices.xlsx"}


def test_resolves_paths_against_another_folder() -> None:
    text = config_to_yaml(small_config(Path("/sessions/old")), Path("/sessions/old"))
    copied = config_from_yaml(text, Path("/sessions/new"))
    assert copied.battery_sheet.path == Path("/sessions/new/battery.xlsx")


def test_writes_datetimes_as_iso_strings() -> None:
    folder = Path("/s")
    document = yaml.safe_load(config_to_yaml(small_config(folder), folder))
    assert document["horizon"]["start"] == "2018-01-01T00:00:00+00:00"
    assert document["horizon"]["window_size"] == "month"
