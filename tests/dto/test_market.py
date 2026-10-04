import dataclasses
from datetime import datetime, timedelta

import pytest

from aurora_er.dto import MarketDTO


def _market_2_first_hours() -> MarketDTO:
    return MarketDTO(
        name="Market 2",
        horizon_start=datetime(2018, 1, 1, 0, 0),
        horizon_end=datetime(2018, 1, 1, 4, 0),
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
            datetime(2018, 1, 1),
            datetime(2018, 1, 1, 1),
            timedelta(hours=1),
            (51.89,),
        )


def test_equal_when_fields_equal() -> None:
    assert _market_2_first_hours() == _market_2_first_hours()
    assert hash(_market_2_first_hours()) == hash(_market_2_first_hours())
