"""Wholesale electricity market prices, as provided in `docs/input/Attachment 2.xlsx`."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from aurora_er.dto.validation import are_finite, is_timezone_aware, require
from aurora_er.timing import elapsed


@dataclass(frozen=True, slots=True, kw_only=True)
class MarketDTO:
    """Price series of one market over a regular time grid.

    The prices at index `i` apply to the interval starting at
    `horizon_start + i * step_length`.
    """

    name: str
    """Identifier of the market, e.g. `"Market 2"`."""

    horizon_start: datetime
    """Start of the first interval, inclusive. Timezone-aware."""

    horizon_end: datetime
    """End of the last interval, exclusive. Timezone-aware."""

    step_length: timedelta
    """Duration of each trading interval; capacity is committed for a whole step."""

    buy_prices_gbp_per_mwh: tuple[float, ...]
    """Price paid per MWh imported when charging, one per step."""

    sell_prices_gbp_per_mwh: tuple[float, ...]
    """Price received per MWh exported when discharging, one per step."""

    @property
    def step_count(self) -> int:
        """Number of trading intervals in the market's horizon."""
        return elapsed(self.horizon_start, self.horizon_end) // self.step_length

    def __post_init__(self) -> None:
        require(bool(self.name.strip()), "name must not be blank")
        require(is_timezone_aware(self.horizon_start), "horizon_start must be timezone-aware")
        require(is_timezone_aware(self.horizon_end), "horizon_end must be timezone-aware")
        horizon_length = elapsed(self.horizon_start, self.horizon_end)
        require(horizon_length > timedelta(0), "horizon_start must be before horizon_end")
        require(self.step_length > timedelta(0), "step_length must be positive")
        require(
            horizon_length % self.step_length == timedelta(0),
            "horizon must be a whole number of steps",
        )
        require(
            len(self.buy_prices_gbp_per_mwh) == self.step_count,
            "buy_prices_gbp_per_mwh must have one price per step",
        )
        require(
            len(self.sell_prices_gbp_per_mwh) == self.step_count,
            "sell_prices_gbp_per_mwh must have one price per step",
        )
        require(are_finite(self.buy_prices_gbp_per_mwh), "buy_prices_gbp_per_mwh must be finite")
        require(are_finite(self.sell_prices_gbp_per_mwh), "sell_prices_gbp_per_mwh must be finite")
