import dataclasses
import math
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from aurora_er.dto import InvalidDTOError, MarketDTO


def _market_2_first_hours() -> MarketDTO:
    return MarketDTO(
        name="Market 2",
        horizon_start=datetime(2018, 1, 1, 0, 0, tzinfo=UTC),
        horizon_end=datetime(2018, 1, 1, 4, 0, tzinfo=UTC),
        step_length=timedelta(hours=1),
        prices_gbp_per_mwh=(51.89, 55.49, 51.06, 44.76),
    )


def test_is_immutable() -> None:
    market = _market_2_first_hours()
    with pytest.raises(dataclasses.FrozenInstanceError):
        market.step_length = timedelta(minutes=30)  # type: ignore[misc]


def test_requires_keyword_arguments() -> None:
    with pytest.raises(TypeError):
        MarketDTO(  # type: ignore[call-arg]
            "Market 2",
            datetime(2018, 1, 1, tzinfo=UTC),
            datetime(2018, 1, 1, 1, tzinfo=UTC),
            timedelta(hours=1),
            (51.89,),
        )


def test_equal_when_fields_equal() -> None:
    assert _market_2_first_hours() == _market_2_first_hours()
    assert hash(_market_2_first_hours()) == hash(_market_2_first_hours())


def test_accepts_market_2_first_hours() -> None:
    assert len(_market_2_first_hours().prices_gbp_per_mwh) == 4


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"name": " "}, "name"),
        ({"horizon_start": datetime(2018, 1, 1)}, "horizon_start must be timezone-aware"),
        ({"horizon_end": datetime(2018, 1, 1, 4)}, "horizon_end must be timezone-aware"),
        ({"horizon_end": datetime(2018, 1, 1, tzinfo=UTC)}, "before horizon_end"),
        ({"step_length": timedelta(0)}, "step_length"),
        ({"step_length": timedelta(minutes=90)}, "whole number of steps"),
        ({"prices_gbp_per_mwh": (51.89, 55.49, 51.06)}, "one price per step"),
        ({"prices_gbp_per_mwh": (51.89, math.nan, 51.06, 44.76)}, "finite"),
        ({"prices_gbp_per_mwh": (51.89, math.inf, 51.06, 44.76)}, "finite"),
    ],
)
def test_rejects_invalid_values(changes: dict[str, Any], message: str) -> None:
    with pytest.raises(InvalidDTOError, match=message):
        dataclasses.replace(_market_2_first_hours(), **changes)


def test_accepts_negative_prices() -> None:
    market = dataclasses.replace(_market_2_first_hours(), prices_gbp_per_mwh=(-68.5, 0, 1, 2))
    assert market.prices_gbp_per_mwh[0] == -68.5
