from datetime import timedelta

import pytest

from aurora_er.dto import MarketDispatchDTO
from aurora_er.solver.extract import cycles_in_horizon, final_state, last_commissioning
from aurora_er.solver.problem import DispatchProblem, prepare_problem
from tests.solver.scenarios import HALF_HOUR, ONE_HOUR, START, battery, hours, market, options


def _two_markets(*, commissioned_hours_before_end_of_life: int = 0) -> DispatchProblem:
    commissioned_at = (
        START.replace(year=2017) + commissioned_hours_before_end_of_life * ONE_HOUR
        if commissioned_hours_before_end_of_life
        else START - timedelta(days=30)
    )
    return prepare_problem(
        battery(
            volume_mwh=2,
            discharging_loss=0.5,
            lifetime_years=1,
            commissioned_at=commissioned_at,
        ),
        hours(2),
        [market("M1", HALF_HOUR, (1,) * 4), market("M2", ONE_HOUR, (1, 1))],
        options(),
    )


def _dispatch(name: str, step: timedelta, discharge: tuple[float, ...]) -> MarketDispatchDTO:
    return MarketDispatchDTO(
        name=name,
        step_length=step,
        charge_mw=(0.0,) * len(discharge),
        discharge_mw=discharge,
        profit_gbp=0.0,
    )


def test_cycles_in_horizon_sums_drained_energy_over_volume() -> None:
    markets = (
        _dispatch("M1", HALF_HOUR, (1.0, 0.0, 0.0, 1.0)),
        _dispatch("M2", ONE_HOUR, (0.5, 0.0)),
    )
    discharged_mwh = 0.5 * 2 + 1 * 0.5
    assert cycles_in_horizon(_two_markets(), markets) == pytest.approx(discharged_mwh / 0.5 / 2)


def test_last_commissioning_keeps_original_without_replacement() -> None:
    problem = _two_markets()
    assert (
        last_commissioning(problem, (0, 0, 0, 0, 0), False) == problem.battery.state.commissioned_at
    )


def test_last_commissioning_at_latest_cycle_replacement() -> None:
    problem = _two_markets()
    assert last_commissioning(problem, (0, 1, 1, 2, 2), False) == START + 3 * HALF_HOUR


def test_last_commissioning_at_calendar_replacement() -> None:
    problem = _two_markets(commissioned_hours_before_end_of_life=1)
    assert problem.calendar_end_boundary == 2
    assert last_commissioning(problem, (0, 0, 0, 0, 0), True) == START + ONE_HOUR


def test_last_commissioning_picks_later_of_cycle_and_calendar() -> None:
    problem = _two_markets(commissioned_hours_before_end_of_life=1)
    assert last_commissioning(problem, (0, 0, 0, 1, 1), True) == START + 3 * HALF_HOUR


def test_final_state_clamps_solver_noise_to_bounds() -> None:
    problem = prepare_problem(
        battery(volume_mwh=1, lifetime_cycles=10, degradation_pct_per_cycle=1),
        hours(1),
        [market("M", ONE_HOUR, (1,))],
        options(),
    )
    state = final_state(
        problem, stored_energy_mwh=1.0, cycles_used=10 + 1e-9, commissioned_at=START
    )
    assert state.cycles_used == 10
    assert state.stored_energy_mwh == pytest.approx(0.9)


def test_final_state_clamps_negative_noise_to_zero() -> None:
    problem = prepare_problem(battery(), hours(1), [market("M", ONE_HOUR, (1,))], options())
    state = final_state(
        problem, stored_energy_mwh=-1e-12, cycles_used=-1e-12, commissioned_at=START
    )
    assert state.stored_energy_mwh == 0
    assert state.cycles_used == 0
