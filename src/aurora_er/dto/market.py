"""Wholesale electricity market prices, as provided in ``docs/input/Attachment 2.xlsx``."""

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True, slots=True, kw_only=True)
class MarketDTO:
    """Price series of one market over a regular time grid.

    The price at index ``i`` applies to the interval starting at
    ``horizon_start + i * step_length``.
    """

    name: str
    """Identifier of the market, e.g. ``"Market 2"``."""

    horizon_start: datetime
    """Start of the first interval, inclusive."""

    horizon_end: datetime
    """End of the last interval, exclusive."""

    step_length: timedelta
    """Duration of each trading interval; capacity is committed for a whole step."""

    prices_gbp_per_mwh: tuple[float, ...]
    """One price per step, in chronological order."""
