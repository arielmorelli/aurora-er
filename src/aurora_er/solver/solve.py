"""Single entry point of the battery dispatch solver."""

from collections.abc import Sequence

from aurora_er.dto import BatteryDTO, DispatchResultDTO, HorizonDTO, MarketDTO, SolveOptionsDTO
from aurora_er.solver.backend import MilpBackend
from aurora_er.solver.extract import build_result
from aurora_er.solver.model import build_model
from aurora_er.solver.problem import prepare_problem
from aurora_er.solver.validation import validate_inputs


def solve(
    battery: BatteryDTO,
    horizon: HorizonDTO,
    markets: Sequence[MarketDTO],
    options: SolveOptionsDTO,
    backend: MilpBackend,
) -> DispatchResultDTO:
    """Find the profit-maximising dispatch of `battery` across `markets` over `horizon`.

    Raises:
        InvalidSolveInputError: the inputs are inconsistent with each other.
        SolverFailedError: `backend` found no solution.
    """
    validate_inputs(battery, horizon, markets)
    problem = prepare_problem(battery, horizon, markets, options)
    model = build_model(problem)
    outcome = backend.solve(model, options)
    return build_result(problem, model, outcome)
