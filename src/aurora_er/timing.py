"""Time arithmetic on timezone-aware datetimes.

Subtracting two datetimes that share a ``tzinfo`` object uses wall-clock time
and ignores daylight-saving shifts, so durations are always computed in UTC.
"""

from datetime import UTC, datetime, timedelta

ONE_HOUR = timedelta(hours=1)


def to_utc(moment: datetime) -> datetime:
    """Return ``moment`` converted to UTC."""
    return moment.astimezone(UTC)


def elapsed(start: datetime, end: datetime) -> timedelta:
    """Real time elapsed from ``start`` to ``end``, across any DST shift."""
    return to_utc(end) - to_utc(start)


def in_hours(duration: timedelta) -> float:
    """``duration`` expressed in hours."""
    return duration / ONE_HOUR


def add_years(moment: datetime, years: int) -> datetime:
    """Same wall-clock time ``years`` later, in ``moment``'s own timezone.

    29 February maps to 28 February in non-leap years.
    """
    target_year = moment.year + years
    try:
        return moment.replace(year=target_year)
    except ValueError:
        return moment.replace(year=target_year, day=moment.day - 1)
