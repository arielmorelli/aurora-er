import dataclasses
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from aurora_er.dto import HorizonDTO
from aurora_er.solver.problem import (
    PreparedMarket,
    calendar_end_boundary,
    calendar_end_of_life,
    cycle_cap,
    initial_capex_gbp,
    opex_gbp,
    prepare_problem,
    replacement_bound,
)
from tests.solver.scenarios import HALF_HOUR, ONE_HOUR, START, battery, hours, market, options

LONDON = ZoneInfo("Europe/London")


def _hourly_market_in_half_hour_grid() -> PreparedMarket:
    return PreparedMarket(
        name="M2",
        step_length=ONE_HOUR,
        base_steps_per_interval=2,
        buy_prices_gbp_per_mwh=(1.0, 2.0),
        sell_prices_gbp_per_mwh=(1.0, 2.0),
    )


def test_prepared_market_interval_count_and_hours() -> None:
    prepared = _hourly_market_in_half_hour_grid()
    assert prepared.interval_count == 2
    assert prepared.interval_hours == 1


def test_prepared_market_maps_base_steps_to_intervals() -> None:
    prepared = _hourly_market_in_half_hour_grid()
    assert [prepared.interval_of(step) for step in range(4)] == [0, 0, 1, 1]


def test_prepare_uses_finest_step_as_base_grid() -> None:
    problem = prepare_problem(
        battery(),
        hours(2),
        [market("M2", ONE_HOUR, (1, 2)), market("M1", HALF_HOUR, (1, 2, 3, 4))],
        options(),
    )
    assert problem.base_step == HALF_HOUR
    assert problem.base_step_count == 4
    assert problem.base_step_hours == 0.5
    assert [m.base_steps_per_interval for m in problem.markets] == [2, 1]
    assert [m.name for m in problem.markets] == ["M2", "M1"]


def test_prepare_slices_prices_to_horizon() -> None:
    problem = prepare_problem(
        battery(),
        hours(2, start=START + ONE_HOUR),
        [market("M", ONE_HOUR, (1, 2, 3, 4), sell_prices=(5, 6, 7, 8))],
        options(),
    )
    assert problem.markets[0].buy_prices_gbp_per_mwh == (2, 3)
    assert problem.markets[0].sell_prices_gbp_per_mwh == (6, 7)


def test_prepare_counts_real_steps_on_clock_change_day() -> None:
    day_start = datetime(2018, 3, 25, tzinfo=LONDON)
    problem = prepare_problem(
        battery(),
        HorizonDTO(start=day_start, end=datetime(2018, 3, 26, tzinfo=LONDON)),
        [market("M", ONE_HOUR, (1,) * 23, start=day_start)],
        options(),
    )
    assert problem.base_step_count == 23


def test_prepare_sets_cycle_cap_only_when_enforced() -> None:
    inputs = (battery(), hours(2), [market("M", ONE_HOUR, (1, 2))])
    assert prepare_problem(*inputs, options()).cycle_cap is None
    assert prepare_problem(*inputs, options(enforce_cycle_pace=True)).cycle_cap is not None


def test_boundary_time_is_in_horizon_timezone() -> None:
    day_start = datetime(2018, 3, 25, tzinfo=LONDON)
    problem = prepare_problem(
        battery(),
        HorizonDTO(start=day_start, end=datetime(2018, 3, 26, tzinfo=LONDON)),
        [market("M", ONE_HOUR, (1,) * 23, start=day_start)],
        options(),
    )
    after_clock_change = problem.boundary_time(2)
    assert after_clock_change == datetime(2018, 3, 25, 3, tzinfo=LONDON)
    assert after_clock_change.tzinfo is LONDON


def test_calendar_end_of_life_adds_lifetime_years() -> None:
    assert calendar_end_of_life(battery(lifetime_years=10, commissioned_at=START)) == START.replace(
        year=2028
    )


def test_calendar_end_boundary_when_inside_horizon() -> None:
    expiring = battery(
        lifetime_years=1, commissioned_at=START.replace(year=2017) + timedelta(minutes=90)
    )
    assert calendar_end_boundary(expiring, hours(4), ONE_HOUR) == 2


def test_calendar_end_boundary_is_none_outside_horizon() -> None:
    assert calendar_end_boundary(battery(), hours(4), ONE_HOUR) is None


def test_calendar_end_boundary_is_none_at_horizon_end() -> None:
    expiring = battery(lifetime_years=1, commissioned_at=START.replace(year=2017) + 4 * ONE_HOUR)
    assert calendar_end_boundary(expiring, hours(4), ONE_HOUR) is None


def test_replacement_bound_covers_maximum_throughput() -> None:
    fast = battery(max_rate_mw=1, volume_mwh=1, lifetime_cycles=2, cycles_used=1)
    assert replacement_bound(fast, timedelta(hours=4)) == 3


def test_replacement_bound_is_at_least_one() -> None:
    assert replacement_bound(battery(lifetime_cycles=1000), ONE_HOUR) == 1


def test_cycle_cap_spreads_remaining_cycles_over_remaining_life() -> None:
    paced = battery(lifetime_years=1, lifetime_cycles=1095, commissioned_at=START)
    assert cycle_cap(paced, hours(4)) == pytest.approx(1095 * 4 / 8760)


def test_cycle_cap_uses_what_is_left() -> None:
    half_used = battery(lifetime_years=1, lifetime_cycles=1000, cycles_used=500)
    remaining_hours = (calendar_end_of_life(half_used) - START) / ONE_HOUR
    assert cycle_cap(half_used, hours(4)) == pytest.approx(500 * 4 / remaining_hours)


def test_initial_capex_only_when_commissioned_at_horizon_start() -> None:
    assert initial_capex_gbp(battery(capex_gbp=100, commissioned_at=START), hours(1)) == 100
    assert initial_capex_gbp(battery(capex_gbp=100), hours(1)) == 0


def test_opex_counts_operating_year_starting_at_commissioning() -> None:
    assert opex_gbp(battery(opex_gbp_per_year=7, commissioned_at=START), hours(1)) == 7


def test_opex_counts_anniversaries_inside_horizon() -> None:
    three_years = HorizonDTO(start=START, end=START.replace(year=2021))
    assert opex_gbp(battery(opex_gbp_per_year=7, commissioned_at=START), three_years) == 21


def test_opex_is_zero_without_anniversary_in_horizon() -> None:
    assert opex_gbp(battery(opex_gbp_per_year=7), hours(1)) == 0


def test_opex_counts_anniversary_of_older_battery() -> None:
    older = battery(opex_gbp_per_year=7, commissioned_at=START.replace(year=2016) + ONE_HOUR)
    assert opex_gbp(older, hours(2)) == 7


def test_problem_is_immutable() -> None:
    problem = prepare_problem(battery(), hours(2), [market("M", ONE_HOUR, (1, 2))], options())
    with pytest.raises(dataclasses.FrozenInstanceError):
        problem.base_step_count = 3  # type: ignore[misc]
