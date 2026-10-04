"""Run configuration: every value a run needs besides the input files' contents."""

from dataclasses import dataclass

from aurora_er.dto import BatteryStateDTO, HorizonDTO, SolveOptionsDTO
from aurora_er.loading import BatterySheet, MarketSheet
from aurora_er.solver import WindowSize


@dataclass(frozen=True, slots=True, kw_only=True)
class RunConfig:
    """Inputs of one dispatch run."""

    battery_sheet: BatterySheet
    """Where the battery parameters are."""

    battery_state: BatteryStateDTO
    """Battery condition at the horizon start."""

    market_sheets: tuple[MarketSheet, ...]
    """Where each market's prices are, in order."""

    horizon: HorizonDTO
    """Whole period to optimise."""

    window_size: WindowSize
    """How much of the horizon is solved at once; windows are solved in order."""

    options: SolveOptionsDTO
    """Modelling switches and solver limits."""
