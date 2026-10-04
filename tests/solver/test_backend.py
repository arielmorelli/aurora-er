import math
from typing import Any

import pyomo.environ as pyo
import pytest
from pyomo.contrib.appsi.base import TerminationCondition

from aurora_er.dto import SolveOptionsDTO, SolveStatus
from aurora_er.solver.backend import HighsBackend, relative_gap, status_for
from aurora_er.solver.errors import SolverFailedError

EXACT = SolveOptionsDTO(enforce_cycle_pace=False, time_limit_seconds=10, mip_gap=0)


def _pick_larger_of_two(*, infeasible: bool) -> Any:
    model = pyo.ConcreteModel()
    model.choose_second = pyo.Var(within=pyo.Binary)
    model.value = pyo.Var(bounds=(0, 10))
    model.link = pyo.Constraint(expr=model.value <= 3 + 4 * model.choose_second)
    if infeasible:
        model.impossible = pyo.Constraint(expr=model.value >= 11)
    model.goal = pyo.Objective(expr=model.value, sense=pyo.maximize)
    return model


def test_highs_solves_and_loads_solution() -> None:
    model = _pick_larger_of_two(infeasible=False)
    outcome = HighsBackend().solve(model, EXACT)
    assert outcome.status is SolveStatus.OPTIMAL
    assert outcome.mip_gap == 0
    assert pyo.value(model.value) == pytest.approx(7)


def test_highs_raises_without_solution() -> None:
    with pytest.raises(SolverFailedError, match="infeasible"):
        HighsBackend().solve(_pick_larger_of_two(infeasible=True), EXACT)


@pytest.mark.parametrize(
    ("termination", "status"),
    [
        (TerminationCondition.optimal, SolveStatus.OPTIMAL),
        (TerminationCondition.maxTimeLimit, SolveStatus.FEASIBLE),
        (TerminationCondition.infeasible, None),
        (TerminationCondition.unbounded, None),
        (TerminationCondition.error, None),
    ],
)
def test_status_for(termination: TerminationCondition, status: SolveStatus | None) -> None:
    assert status_for(termination) is status


@pytest.mark.parametrize(
    ("objective", "bound", "gap"),
    [
        (100.0, 100.0, 0.0),
        (100.0, 110.0, 0.1),
        (-100.0, -90.0, 0.1),
        (0.0, 0.0, 0.0),
        (0.0, 5.0, math.inf),
    ],
)
def test_relative_gap(objective: float, bound: float, gap: float) -> None:
    assert relative_gap(objective, bound) == pytest.approx(gap)
