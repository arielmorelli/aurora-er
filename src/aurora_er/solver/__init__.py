"""Battery dispatch solver: a MILP built with Pyomo, solved by an injected backend."""

from aurora_er.solver.backend import BackendOutcome, HighsBackend, MilpBackend
from aurora_er.solver.errors import InvalidSolveInputError, SolverFailedError
from aurora_er.solver.rolling import (
    WindowSize,
    fixed_windows,
    monthly_windows,
    rolling_windows,
    solve_rolling,
)
from aurora_er.solver.solve import solve

__all__ = [
    "BackendOutcome",
    "HighsBackend",
    "InvalidSolveInputError",
    "MilpBackend",
    "SolverFailedError",
    "WindowSize",
    "fixed_windows",
    "monthly_windows",
    "rolling_windows",
    "solve",
    "solve_rolling",
]
