"""Errors raised by the solver."""


class InvalidSolveInputError(ValueError):
    """The input DTOs are individually valid but inconsistent with each other."""


class SolverFailedError(RuntimeError):
    """The optimisation backend returned no usable solution."""
