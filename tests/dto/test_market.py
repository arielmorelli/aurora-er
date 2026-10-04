import dataclasses
import math
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from aurora_er.dto import InvalidDTOError, MarketDTO

MARKET_2_FIRST_PRICES = (51.89, 55.49, 51.06, 44.76)


def _market_2_first_hours() -> MarketDTO:
    return MarketDTO(
        name="Market 2",
        horizon_start=datetime(2018, 1, 1, 0, 0, tzinfo=UTC),
        horizon_end=datetime(2018, 1, 1, 4, 0, tzinfo=UTC),
        step_length=timedelta(hours=1),
        buy_prices_gbp_per_mwh=MARKET_2_FIRST_PRICES,
        sell_prices_gbp_per_mwh=MARKET_2_FIRST_PRICES,
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
            (51.89,),
        )


def test_equal_when_fields_equal() -> None:
    assert _market_2_first_hours() == _market_2_first_hours()
    assert hash(_market_2_first_hours()) == hash(_market_2_first_hours())


def test_step_count_is_number_of_intervals() -> None:
    assert _market_2_first_hours().step_count == 4


def test_step_count_uses_real_time_across_clock_change() -> None:
    london = ZoneInfo("Europe/London")
    market = MarketDTO(
        name="Market 2",
        horizon_start=datetime(2018, 3, 25, 0, 0, tzinfo=london),
        horizon_end=datetime(2018, 3, 25, 3, 0, tzinfo=london),
        step_length=timedelta(hours=1),
        buy_prices_gbp_per_mwh=(1.0, 2.0),
        sell_prices_gbp_per_mwh=(1.0, 2.0),
    )
    assert market.step_count == 2


def test_accepts_negative_prices() -> None:
    negative = (-68.5, 0.0, 1.0, 2.0)
    market = dataclasses.replace(
        _market_2_first_hours(),
        buy_prices_gbp_per_mwh=negative,
        sell_prices_gbp_per_mwh=negative,
    )
    assert market.buy_prices_gbp_per_mwh[0] == -68.5


def test_accepts_different_buy_and_sell_prices() -> None:
    market = dataclasses.replace(
        _market_2_first_hours(), sell_prices_gbp_per_mwh=(50.0, 54.0, 50.0, 43.0)
    )
    assert market.buy_prices_gbp_per_mwh != market.sell_prices_gbp_per_mwh


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"name": " "}, "name"),
        ({"horizon_start": datetime(2018, 1, 1)}, "horizon_start must be timezone-aware"),
        ({"horizon_end": datetime(2018, 1, 1, 4)}, "horizon_end must be timezone-aware"),
        ({"horizon_end": datetime(2018, 1, 1, tzinfo=UTC)}, "before horizon_end"),
        ({"step_length": timedelta(0)}, "step_length"),
        ({"step_length": timedelta(minutes=90)}, "whole number of steps"),
        ({"buy_prices_gbp_per_mwh": (1.0, 2.0, 3.0)}, "buy_prices_gbp_per_mwh must have one"),
        ({"sell_prices_gbp_per_mwh": (1.0, 2.0, 3.0)}, "sell_prices_gbp_per_mwh must have one"),
        ({"buy_prices_gbp_per_mwh": (1.0, math.nan, 3.0, 4.0)}, "buy_prices.*finite"),
        ({"sell_prices_gbp_per_mwh": (1.0, math.inf, 3.0, 4.0)}, "sell_prices.*finite"),
    ],
)
def test_rejects_invalid_values(changes: dict[str, Any], message: str) -> None:
    with pytest.raises(InvalidDTOError, match=message):
        dataclasses.replace(_market_2_first_hours(), **changes)
