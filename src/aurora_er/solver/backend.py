"""Optimisation backends that solve a built Pyomo model in place."""

import math
from dataclasses import dataclass
from typing import Any, Protocol

from pyomo.contrib.appsi.base import TerminationCondition
from pyomo.contrib.appsi.solvers import Highs

from aurora_er.dto import SolveOptionsDTO, SolveStatus
from aurora_er.solver.errors import SolverFailedError


@dataclass(frozen=True, slots=True, kw_only=True)
class BackendOutcome:
    """What the backend reports after loading a solution into the model."""

    status: SolveStatus
    """Whether the loaded solution is proven optimal."""

    mip_gap: float
    """Relative gap between the loaded solution and the best bound."""


class MilpBackend(Protocol):
    """Solves a Pyomo model and loads the solution into its variables."""

    def solve(self, model: Any, options: SolveOptionsDTO) -> BackendOutcome:
        """Solve ``model`` within ``options``; raise :class:`SolverFailedError` if unsolved."""
        ...


class HighsBackend:
    """HiGHS through Pyomo's in-process ``appsi`` interface."""

    def solve(self, model: Any, options: SolveOptionsDTO) -> BackendOutcome:
        """Solve ``model`` with HiGHS and load the best solution found."""
        solver = Highs()
        solver.config.load_solution = False
        solver.config.stream_solver = False
        solver.config.time_limit = options.time_limit_seconds
        solver.config.mip_gap = options.mip_gap
        results = solver.solve(model)
        status = status_for(results.termination_condition)
        if status is None or results.best_feasible_objective is None:
            raise SolverFailedError(f"HiGHS returned no solution: {results.termination_condition}")
        results.solution_loader.load_vars()
        return BackendOutcome(
            status=status,
            mip_gap=relative_gap(results.best_feasible_objective, results.best_objective_bound),
        )


def status_for(termination: TerminationCondition) -> SolveStatus | None:
    """Map a solver termination to a result status; ``None`` if no solution can be trusted."""
    if termination == TerminationCondition.optimal:
        return SolveStatus.OPTIMAL
    if termination == TerminationCondition.maxTimeLimit:
        return SolveStatus.FEASIBLE
    return None


def relative_gap(objective: float, bound: float) -> float:
    """``|bound - objective| / |objective|``, as HiGHS defines the MIP gap."""
    if objective == bound:
        return 0.0
    if objective == 0:
        return math.inf
    return abs(bound - objective) / abs(objective)
