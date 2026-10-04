"""Session status as stored in the plain-text `status` file."""

from dataclasses import dataclass
from enum import StrEnum


class SessionState(StrEnum):
    """Where a session is in its life."""

    RUNNING = "running"
    """A worker is solving it."""

    DONE = "done"
    """Solved; the result file exists."""

    CANCELLED = "cancelled"
    """Stopped on request before finishing."""

    ERROR = "error"
    """Stopped by an error; the detail holds its description."""

    INTERRUPTED = "interrupted"
    """Was running when the app stopped, so it never finished."""


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionStatus:
    """Content of a `status` file."""

    state: SessionState
    """Current state."""

    detail: str
    """Description for errors; empty otherwise."""


def format_status(status: SessionStatus) -> str:
    """File content: the state on the first line, then the detail if any."""
    if status.detail:
        return f"{status.state.value}\n{status.detail}\n"
    return f"{status.state.value}\n"


def parse_status(text: str) -> SessionStatus:
    """Read a `status` file's content."""
    first_line, _, rest = text.partition("\n")
    return SessionStatus(state=SessionState(first_line.strip()), detail=rest.strip())
