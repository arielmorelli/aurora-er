import pyomo.environ as pyo
import pytest

from aurora_er.solver.model import (
    build_model,
    drained_cycles,
    total_charge_mw,
    total_discharge_mw,
)
from aurora_er.solver.problem import DispatchProblem, prepare_problem
from tests.solver.scenarios import HALF_HOUR, ONE_HOUR, START, battery, hours, market, options


def _two_markets_over_one_hour(*, enforce_cycle_pace: bool = False) -> DispatchProblem:
    return prepare_problem(
        battery(discharging_loss=0.2, volume_mwh=2, stored_energy_mwh=0.5, cycles_used=3),
        hours(1),
        [market("M1", HALF_HOUR, (1, 2)), market("M2", ONE_HOUR, (3,))],
        options(enforce_cycle_pace=enforce_cycle_pace),
    )


def _expiring_during_horizon() -> DispatchProblem:
    return prepare_problem(
        battery(lifetime_years=1, commissioned_at=START.replace(year=2017) + ONE_HOUR),
        hours(2),
        [market("M", ONE_HOUR, (1, 2))],
        options(),
    )


def test_one_binary_per_base_step() -> None:
    model = build_model(_two_markets_over_one_hour())
    assert len(model.charging) == 2
    assert all(model.charging[step].is_binary() for step in model.steps)


def test_power_variables_follow_market_intervals() -> None:
    model = build_model(_two_markets_over_one_hour())
    assert sorted(model.charge.keys()) == [(0, 0), (0, 1), (1, 0)]
    assert model.charge[0, 0].ub == 1
    assert model.discharge[1, 0].ub == 1


def test_initial_state_is_fixed() -> None:
    model = build_model(_two_markets_over_one_hour())
    assert model.stored[0].fixed and model.stored[0].value == 0.5
    assert model.cycles[0].fixed and model.cycles[0].value == 3
    assert model.replaced[0].fixed and model.replaced[0].value == 0


def test_hourly_commitment_appears_in_both_half_hours() -> None:
    problem = _two_markets_over_one_hour()
    model = build_model(problem)
    model.charge[0, 0].value = 0.25
    model.charge[0, 1].value = 0.5
    model.charge[1, 0].value = 0.125
    assert pyo.value(total_charge_mw(model, problem, 0)) == pytest.approx(0.375)
    assert pyo.value(total_charge_mw(model, problem, 1)) == pytest.approx(0.625)


def test_drained_cycles_include_discharge_loss() -> None:
    problem = _two_markets_over_one_hour()
    model = build_model(problem)
    model.discharge[0, 0].value = 0.4
    model.discharge[1, 0].value = 0.4
    assert pyo.value(total_discharge_mw(model, problem, 0)) == pytest.approx(0.8)
    assert pyo.value(drained_cycles(model, problem, 0)) == pytest.approx(0.5 * 0.8 / 0.8 / 2)


def test_no_calendar_variables_when_life_ends_after_horizon() -> None:
    model = build_model(_two_markets_over_one_hour())
    assert not hasattr(model, "replaced_before_calendar_end")
    assert not hasattr(model, "calendar_resets_cycles")


def test_calendar_variables_when_life_ends_in_horizon() -> None:
    model = build_model(_expiring_during_horizon())
    assert model.replaced_before_calendar_end.is_binary()
    assert hasattr(model, "calendar_resets_cycles")


def test_cycle_pace_constraint_only_when_enforced() -> None:
    assert not hasattr(build_model(_two_markets_over_one_hour()), "cycle_pace")
    assert hasattr(build_model(_two_markets_over_one_hour(enforce_cycle_pace=True)), "cycle_pace")


def test_objective_maximises_profit() -> None:
    assert build_model(_two_markets_over_one_hour()).profit.sense == pyo.maximize
