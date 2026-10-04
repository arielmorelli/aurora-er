"""Run configuration: every value a run needs besides the input files' contents."""

from dataclasses import dataclass

from aurora_er.dto import BatteryStateDTO, HorizonDTO, SolveOptionsDTO
from aurora_er.loading import BatterySheet, MarketSheet


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

    months_per_window: int
    """Calendar months solved together; the horizon is solved window by window."""

    options: SolveOptionsDTO
    """Modelling switches and solver limits."""
