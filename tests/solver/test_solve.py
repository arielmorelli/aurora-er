from typing import Any

import pytest

from aurora_er.dto import SolveOptionsDTO, SolveStatus
from aurora_er.solver import (
    BackendOutcome,
    HighsBackend,
    InvalidSolveInputError,
    SolverFailedError,
    solve,
)
from tests.solver.rules import assert_follows_brief
from tests.solver.scenarios import (
    HALF_HOUR,
    ONE_HOUR,
    START,
    battery,
    hours,
    market,
    options,
)

LOW_HIGH_LOW_HIGH = (0.0, 10.0, 0.0, 10.0)
THREE_CYCLES = (*LOW_HIGH_LOW_HIGH, 0.0, 10.0)


class _ReportsTimeLimit:
    def solve(self, model: Any, options: SolveOptionsDTO) -> BackendOutcome:
        HighsBackend().solve(model, options)
        return BackendOutcome(status=SolveStatus.FEASIBLE, mip_gap=0.05)


class _FindsNothing:
    def solve(self, model: Any, options: SolveOptionsDTO) -> BackendOutcome:
        raise SolverFailedError("no solution")


def test_buys_low_and_sells_high() -> None:
    result = solve(
        battery(), hours(2), [market("M", ONE_HOUR, (10, 50))], options(), HighsBackend()
    )
    assert result.status is SolveStatus.OPTIMAL
    assert result.market_profit_gbp == pytest.approx(40)
    assert result.markets[0].charge_mw == pytest.approx((1, 0))
    assert result.markets[0].discharge_mw == pytest.approx((0, 1))
    assert result.stored_energy_mwh == pytest.approx((0, 1, 0))
    assert result.cycles_used_in_horizon == pytest.approx(1)


def test_losses_reduce_the_energy_sold() -> None:
    result = solve(
        battery(charging_loss=0.1, discharging_loss=0.1),
        hours(2),
        [market("M", ONE_HOUR, (10, 50))],
        options(),
        HighsBackend(),
    )
    assert result.stored_energy_mwh == pytest.approx((0, 0.9, 0))
    assert result.markets[0].discharge_mw == pytest.approx((0, 0.81))
    assert result.market_profit_gbp == pytest.approx(0.81 * 50 - 10)


def test_stays_idle_when_spread_does_not_cover_losses() -> None:
    result = solve(
        battery(charging_loss=0.1, discharging_loss=0.1),
        hours(2),
        [market("M", ONE_HOUR, (30, 30))],
        options(),
        HighsBackend(),
    )
    assert result.market_profit_gbp == pytest.approx(0)
    assert result.cycles_used_in_horizon == pytest.approx(0)


def test_never_charges_and_discharges_at_the_same_time_across_markets() -> None:
    result = solve(
        battery(),
        hours(1),
        [market("Negative", ONE_HOUR, (-10,)), market("Positive", ONE_HOUR, (20,))],
        options(),
        HighsBackend(),
    )
    assert result.markets[0].charge_mw == pytest.approx((1,))
    assert result.markets[1].discharge_mw == pytest.approx((0,))
    assert result.market_profit_gbp == pytest.approx(10)


def test_splits_power_across_markets_as_in_the_brief() -> None:
    inputs = battery(max_rate_mw=5, volume_mwh=5, stored_energy_mwh=5)
    markets = [market("M1", HALF_HOUR, (100, 100)), market("M2", ONE_HOUR, (100,))]
    result = solve(inputs, hours(1), markets, options(), HighsBackend())
    assert_follows_brief(result, inputs, markets)
    half_hourly, hourly = result.markets
    for half in range(2):
        assert half_hourly.discharge_mw[half] + hourly.discharge_mw[0] <= 5 + 1e-9
    assert result.market_profit_gbp == pytest.approx(500)
    assert result.stored_energy_mwh[-1] == pytest.approx(0)


def test_hourly_commitment_cannot_be_split_into_half_hours() -> None:
    result = solve(
        battery(stored_energy_mwh=1),
        hours(1),
        [market("M1", HALF_HOUR, (100, 0)), market("M2", ONE_HOUR, (60,))],
        options(),
        HighsBackend(),
    )
    assert result.markets[1].discharge_mw == pytest.approx((1,))
    assert result.markets[0].discharge_mw == pytest.approx((0, 0))
    assert result.market_profit_gbp == pytest.approx(60)


def test_degradation_shrinks_usable_volume_per_cycle() -> None:
    inputs = battery(degradation_pct_per_cycle=10, lifetime_cycles=5)
    markets = [market("M", ONE_HOUR, LOW_HIGH_LOW_HIGH)]
    result = solve(inputs, hours(4), markets, options(), HighsBackend())
    assert_follows_brief(result, inputs, markets)
    assert result.stored_energy_mwh == pytest.approx((0, 1, 0, 0.9, 0))
    assert result.market_profit_gbp == pytest.approx(19)


def test_cycles_only_when_the_spread_pays_for_the_wear() -> None:
    ten_pounds_per_cycle = battery(lifetime_cycles=10, capex_gbp=100)
    below = solve(
        ten_pounds_per_cycle, hours(2), [market("M", ONE_HOUR, (0, 9))], options(), HighsBackend()
    )
    above = solve(
        ten_pounds_per_cycle, hours(2), [market("M", ONE_HOUR, (0, 11))], options(), HighsBackend()
    )
    assert below.cycles_used_in_horizon == pytest.approx(0)
    assert above.cycles_used_in_horizon == pytest.approx(1)
    assert above.battery_value_end_gbp == pytest.approx(90)
    assert above.net_profit_gbp == pytest.approx(11 - 10)


def test_replaces_battery_when_extra_cycles_pay_for_the_wear() -> None:
    result = solve(
        battery(lifetime_cycles=2, capex_gbp=5),
        hours(6),
        [market("M", ONE_HOUR, THREE_CYCLES)],
        options(),
        HighsBackend(),
    )
    assert result.replacements == 1
    assert result.market_profit_gbp == pytest.approx(30)
    assert result.capex_gbp == pytest.approx(5)
    assert result.battery_value_start_gbp == pytest.approx(5)
    assert result.battery_value_end_gbp == pytest.approx(5 * (2 - 1) / 2)
    assert result.net_profit_gbp == pytest.approx(30 - 5 + 2.5 - 5)


def test_skips_cycles_that_earn_less_than_their_wear() -> None:
    result = solve(
        battery(lifetime_cycles=1, capex_gbp=15),
        hours(4),
        [market("M", ONE_HOUR, LOW_HIGH_LOW_HIGH)],
        options(),
        HighsBackend(),
    )
    assert result.replacements == 0
    assert result.market_profit_gbp == pytest.approx(0)
    assert result.cycles_used_in_horizon == pytest.approx(0)


def test_cycle_replacement_restarts_commissioning_and_cycles() -> None:
    result = solve(
        battery(lifetime_cycles=2, capex_gbp=5),
        hours(6),
        [market("M", ONE_HOUR, THREE_CYCLES)],
        options(),
        HighsBackend(),
    )
    assert result.final_state.cycles_used == pytest.approx(1)
    assert START + 3 * ONE_HOUR < result.final_state.commissioned_at <= START + 6 * ONE_HOUR


def test_calendar_end_of_life_replaces_battery_and_restores_volume() -> None:
    result = solve(
        battery(
            lifetime_years=1,
            lifetime_cycles=5,
            degradation_pct_per_cycle=10,
            cycles_used=4,
            capex_gbp=1,
            commissioned_at=START.replace(year=2017) + 2 * ONE_HOUR,
        ),
        hours(4),
        [market("M", ONE_HOUR, LOW_HIGH_LOW_HIGH)],
        options(),
        HighsBackend(),
    )
    assert result.replacements == 1
    assert result.capex_gbp == pytest.approx(1)
    assert result.stored_energy_mwh == pytest.approx((0, 0.6, 0, 1, 0))
    assert result.market_profit_gbp == pytest.approx(16)
    assert result.final_state.commissioned_at == START + 2 * ONE_HOUR
    assert result.final_state.cycles_used == pytest.approx(1)


def test_cycle_pace_caps_cycles_in_the_horizon() -> None:
    paced_battery = battery(lifetime_years=1, lifetime_cycles=1095, commissioned_at=START)
    prices = [market("M", ONE_HOUR, LOW_HIGH_LOW_HIGH)]
    paced = solve(paced_battery, hours(4), prices, options(enforce_cycle_pace=True), HighsBackend())
    free = solve(paced_battery, hours(4), prices, options(), HighsBackend())
    assert paced.cycles_used_in_horizon == pytest.approx(0.5)
    assert paced.market_profit_gbp == pytest.approx(5)
    assert free.market_profit_gbp == pytest.approx(20)


def test_cycle_pace_changes_nothing_when_cap_is_not_reached() -> None:
    roomy_battery = battery(lifetime_years=1, lifetime_cycles=1_000_000, commissioned_at=START)
    prices = [market("M", ONE_HOUR, LOW_HIGH_LOW_HIGH)]
    paced = solve(roomy_battery, hours(4), prices, options(enforce_cycle_pace=True), HighsBackend())
    free = solve(roomy_battery, hours(4), prices, options(), HighsBackend())
    assert paced.market_profit_gbp == pytest.approx(free.market_profit_gbp)
    assert paced.cycles_used_in_horizon == pytest.approx(free.cycles_used_in_horizon)


def test_reports_initial_capex_and_opex() -> None:
    result = solve(
        battery(capex_gbp=100, opex_gbp_per_year=7, commissioned_at=START),
        hours(2),
        [market("M", ONE_HOUR, (10, 50))],
        options(),
        HighsBackend(),
    )
    assert result.capex_gbp == pytest.approx(100)
    assert result.opex_gbp == pytest.approx(7)
    assert result.battery_value_start_gbp == 0
    assert result.battery_value_end_gbp == pytest.approx(100 * 999 / 1000)
    assert result.net_profit_gbp == pytest.approx(40 - 100 - 7 + 99.9)


def test_result_follows_each_market_step() -> None:
    result = solve(
        battery(),
        hours(2),
        [market("M1", HALF_HOUR, (1, 2, 3, 4)), market("M2", ONE_HOUR, (1, 2))],
        options(),
        HighsBackend(),
    )
    assert [len(m.charge_mw) for m in result.markets] == [4, 2]
    assert [m.step_length for m in result.markets] == [HALF_HOUR, ONE_HOUR]
    assert result.energy_step_length == HALF_HOUR
    assert len(result.stored_energy_mwh) == 5


def test_uses_only_prices_inside_the_horizon() -> None:
    result = solve(
        battery(),
        hours(2, start=START + 2 * ONE_HOUR),
        [market("M", ONE_HOUR, (0, 1000, 10, 50))],
        options(),
        HighsBackend(),
    )
    assert result.market_profit_gbp == pytest.approx(40)


def test_reports_the_backend_status_and_gap() -> None:
    result = solve(
        battery(), hours(2), [market("M", ONE_HOUR, (10, 50))], options(), _ReportsTimeLimit()
    )
    assert result.status is SolveStatus.FEASIBLE
    assert result.mip_gap == 0.05


def test_propagates_backend_failure() -> None:
    with pytest.raises(SolverFailedError):
        solve(battery(), hours(2), [market("M", ONE_HOUR, (10, 50))], options(), _FindsNothing())


def test_rejects_inconsistent_inputs_before_solving() -> None:
    with pytest.raises(InvalidSolveInputError):
        solve(battery(), hours(3), [market("M", ONE_HOUR, (10, 50))], options(), _FindsNothing())


def test_does_not_modify_inputs() -> None:
    inputs = battery()
    solve(inputs, hours(2), [market("M", ONE_HOUR, (10, 50))], options(), HighsBackend())
    assert inputs == battery()
