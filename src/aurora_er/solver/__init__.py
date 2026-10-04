"""Battery dispatch solver: a MILP built with Pyomo, solved by an injected backend."""

from aurora_er.solver.backend import BackendOutcome, HighsBackend, MilpBackend
from aurora_er.solver.errors import InvalidSolveInputError, SolverFailedError
from aurora_er.solver.rolling import monthly_windows, solve_rolling
from aurora_er.solver.solve import solve

__all__ = [
    "BackendOutcome",
    "HighsBackend",
    "InvalidSolveInputError",
    "MilpBackend",
    "SolverFailedError",
    "monthly_windows",
    "solve",
    "solve_rolling",
]
