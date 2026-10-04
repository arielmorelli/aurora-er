import dataclasses
from typing import Any

import pytest

from aurora_er.dto import InvalidDTOError, SolveOptionsDTO


def _one_minute_exact() -> SolveOptionsDTO:
    return SolveOptionsDTO(enforce_cycle_pace=False, time_limit_seconds=60, mip_gap=0)


def test_is_immutable() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        _one_minute_exact().mip_gap = 0.1  # type: ignore[misc]


def test_requires_every_field() -> None:
    with pytest.raises(TypeError):
        SolveOptionsDTO(enforce_cycle_pace=False, time_limit_seconds=60)  # type: ignore[call-arg]


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"time_limit_seconds": 0}, "time_limit_seconds"),
        ({"mip_gap": -0.01}, "mip_gap"),
        ({"mip_gap": 1}, "mip_gap"),
    ],
)
def test_rejects_invalid_values(changes: dict[str, Any], message: str) -> None:
    with pytest.raises(InvalidDTOError, match=message):
        dataclasses.replace(_one_minute_exact(), **changes)
