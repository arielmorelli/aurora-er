"""Time window over which the battery is dispatched."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from aurora_er.dto.validation import is_timezone_aware, require
from aurora_er.timing import elapsed


@dataclass(frozen=True, slots=True, kw_only=True)
class HorizonDTO:
    """A half-open time window `[start, end)`."""

    start: datetime
    """First instant of the window, inclusive. Timezone-aware."""

    end: datetime
    """End of the window, exclusive. Timezone-aware."""

    @property
    def length(self) -> timedelta:
        """Real time covered by the window, across any DST shift."""
        return elapsed(self.start, self.end)

    def __post_init__(self) -> None:
        require(is_timezone_aware(self.start), "start must be timezone-aware")
        require(is_timezone_aware(self.end), "end must be timezone-aware")
        require(self.length > timedelta(0), "start must be before end")
