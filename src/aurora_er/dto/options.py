"""Settings for a single solve."""

from dataclasses import dataclass

from aurora_er.dto.validation import require


@dataclass(frozen=True, slots=True, kw_only=True)
class SolveOptionsDTO:
    """Modelling switches and solver limits for one call to the solver."""

    enforce_cycle_pace: bool
    """Cap cycles in the horizon to the remaining cycles spread over the remaining calendar life."""

    time_limit_seconds: float
    """Wall-clock limit for the solver; the best solution found so far is returned."""

    mip_gap: float
    """Relative optimality gap at which the solver may stop, as a fraction."""

    def __post_init__(self) -> None:
        require(self.time_limit_seconds > 0, "time_limit_seconds must be positive")
        require(0 <= self.mip_gap < 1, "mip_gap must be in [0, 1)")
