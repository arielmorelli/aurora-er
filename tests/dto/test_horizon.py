import dataclasses
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from aurora_er.dto import HorizonDTO, InvalidDTOError


def _first_day_of_2018() -> HorizonDTO:
    return HorizonDTO(start=datetime(2018, 1, 1, tzinfo=UTC), end=datetime(2018, 1, 2, tzinfo=UTC))


def test_is_immutable() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        _first_day_of_2018().end = datetime(2018, 1, 3, tzinfo=UTC)  # type: ignore[misc]


def test_length() -> None:
    assert _first_day_of_2018().length == timedelta(days=1)


def test_length_uses_real_time_across_clock_change() -> None:
    london = ZoneInfo("Europe/London")
    horizon = HorizonDTO(
        start=datetime(2018, 3, 25, tzinfo=london), end=datetime(2018, 3, 26, tzinfo=london)
    )
    assert horizon.length == timedelta(hours=23)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"start": datetime(2018, 1, 1)}, "start must be timezone-aware"),
        ({"end": datetime(2018, 1, 2)}, "end must be timezone-aware"),
        ({"end": datetime(2018, 1, 1, tzinfo=UTC)}, "before end"),
        ({"end": datetime(2017, 12, 31, tzinfo=UTC)}, "before end"),
    ],
)
def test_rejects_invalid_values(changes: dict[str, Any], message: str) -> None:
    with pytest.raises(InvalidDTOError, match=message):
        dataclasses.replace(_first_day_of_2018(), **changes)
