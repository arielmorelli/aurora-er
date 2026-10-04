"""Session identifiers: the UTC creation time, to the microsecond."""

from datetime import UTC, datetime

from aurora_er.dto.validation import is_timezone_aware
from aurora_er.timing import to_utc

FORMAT = "%Y%m%dT%H%M%S.%fZ"


def new_session_id(now: datetime) -> str:
    """Identifier for a session created at `now` (timezone-aware)."""
    if not is_timezone_aware(now):
        raise ValueError("now must be timezone-aware")
    return to_utc(now).strftime(FORMAT)


def created_at(session_id: str) -> datetime:
    """When the session `session_id` was created, in UTC."""
    return datetime.strptime(session_id, FORMAT).replace(tzinfo=UTC)
