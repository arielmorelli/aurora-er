"""Composition root: wires loaders, solver and backend for one run."""

from collections.abc import Callable
from dataclasses import dataclass

from aurora_er.config import RunConfig
from aurora_er.dto import BatteryDTO, DispatchResultDTO, RollingDispatchResultDTO
from aurora_er.loading import LoadedMarket, read_battery_spec, read_market
from aurora_er.solver import MilpBackend, monthly_windows, solve_rolling


@dataclass(frozen=True, slots=True, kw_only=True)
class RunOutcome:
    """Result of a run together with what was loaded to produce it."""

    result: RollingDispatchResultDTO
    """Dispatch per window and totals."""

    loaded_markets: tuple[LoadedMarket, ...]
    """Markets as read from file, with any timestamp warnings."""


def run(
    config: RunConfig,
    backend: MilpBackend,
    on_window_solved: Callable[[DispatchResultDTO], None],
) -> RunOutcome:
    """Load the inputs named in `config` and solve its horizon window by window."""
    battery = BatteryDTO(spec=read_battery_spec(config.battery_sheet), state=config.battery_state)
    loaded_markets = tuple(read_market(sheet) for sheet in config.market_sheets)
    result = solve_rolling(
        battery,
        monthly_windows(config.horizon, config.months_per_window),
        [loaded.market for loaded in loaded_markets],
        config.options,
        backend,
        on_window_solved,
    )
    return RunOutcome(result=result, loaded_markets=loaded_markets)
