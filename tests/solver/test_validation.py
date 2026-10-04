from datetime import timedelta

import pytest

from aurora_er.dto import HorizonDTO, MarketDTO
from aurora_er.solver.errors import InvalidSolveInputError
from aurora_er.solver.validation import validate_inputs
from tests.solver.scenarios import HALF_HOUR, ONE_HOUR, START, battery, hours, market


def _two_hour_market(name: str = "M") -> MarketDTO:
    return market(name, ONE_HOUR, (1, 2))


def test_accepts_consistent_inputs() -> None:
    validate_inputs(battery(), hours(2), [_two_hour_market(), market("H", HALF_HOUR, (1,) * 4)])


def test_rejects_no_markets() -> None:
    with pytest.raises(InvalidSolveInputError, match="at least one market"):
        validate_inputs(battery(), hours(2), [])


def test_rejects_duplicate_market_names() -> None:
    with pytest.raises(InvalidSolveInputError, match="unique"):
        validate_inputs(battery(), hours(2), [_two_hour_market(), _two_hour_market()])


def test_rejects_market_ending_before_horizon() -> None:
    with pytest.raises(InvalidSolveInputError, match="does not cover"):
        validate_inputs(battery(), hours(3), [_two_hour_market()])


def test_rejects_market_starting_after_horizon() -> None:
    late = market("M", ONE_HOUR, (1, 2), start=START + ONE_HOUR)
    with pytest.raises(InvalidSolveInputError, match="does not cover"):
        validate_inputs(battery(), hours(2), [late])


def test_rejects_horizon_cutting_a_market_interval() -> None:
    half_past = HorizonDTO(start=START + HALF_HOUR, end=START + 2 * ONE_HOUR)
    with pytest.raises(InvalidSolveInputError, match="align"):
        validate_inputs(battery(), half_past, [_two_hour_market()])


def test_rejects_steps_that_do_not_nest() -> None:
    forty_minutes = market("F", timedelta(minutes=40), (1,) * 3)
    twenty_five = market("T", timedelta(minutes=25), (1,) * 24)
    with pytest.raises(InvalidSolveInputError, match="whole multiple"):
        validate_inputs(battery(), hours(2), [forty_minutes, twenty_five])


def test_rejects_horizon_longer_than_lifetime() -> None:
    three_years = market("M", timedelta(days=365), (1, 1, 1))
    with pytest.raises(InvalidSolveInputError, match="lifetime_years"):
        validate_inputs(
            battery(lifetime_years=2, commissioned_at=START),
            HorizonDTO(start=START, end=START + timedelta(days=3 * 365)),
            [three_years],
        )


def test_rejects_battery_commissioned_after_horizon_start() -> None:
    with pytest.raises(InvalidSolveInputError, match="commissioned"):
        validate_inputs(battery(commissioned_at=START + ONE_HOUR), hours(2), [_two_hour_market()])


def test_rejects_battery_past_calendar_life() -> None:
    with pytest.raises(InvalidSolveInputError, match="calendar life"):
        validate_inputs(
            battery(lifetime_years=1, commissioned_at=START.replace(year=2017)),
            hours(2),
            [_two_hour_market()],
        )
