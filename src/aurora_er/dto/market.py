"""Wholesale electricity market prices, as provided in ``docs/input/Attachment 2.xlsx``."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from aurora_er.dto.validation import are_finite, is_timezone_aware, require


@dataclass(frozen=True, slots=True, kw_only=True)
class MarketDTO:
    """Price series of one market over a regular time grid.

    The price at index ``i`` applies to the interval starting at
    ``horizon_start + i * step_length``.
    """

    name: str
    """Identifier of the market, e.g. ``"Market 2"``."""

    horizon_start: datetime
    """Start of the first interval, inclusive. Timezone-aware."""

    horizon_end: datetime
    """End of the last interval, exclusive. Timezone-aware."""

    step_length: timedelta
    """Duration of each trading interval; capacity is committed for a whole step."""

    prices_gbp_per_mwh: tuple[float, ...]
    """One price per step, in chronological order."""

    def __post_init__(self) -> None:
        require(bool(self.name.strip()), "name must not be blank")
        require(is_timezone_aware(self.horizon_start), "horizon_start must be timezone-aware")
        require(is_timezone_aware(self.horizon_end), "horizon_end must be timezone-aware")
        require(self.horizon_start < self.horizon_end, "horizon_start must be before horizon_end")
        require(self.step_length > timedelta(0), "step_length must be positive")
        horizon_length = self.horizon_end - self.horizon_start
        require(
            horizon_length % self.step_length == timedelta(0),
            "horizon must be a whole number of steps",
        )
        require(
            len(self.prices_gbp_per_mwh) == horizon_length // self.step_length,
            "prices_gbp_per_mwh must have one price per step",
        )
        require(are_finite(self.prices_gbp_per_mwh), "prices_gbp_per_mwh must be finite")
