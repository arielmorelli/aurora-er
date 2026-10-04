import pytest

from aurora_er.sessions import SessionState, SessionStatus
from aurora_er.sessions.status import format_status, parse_status


def test_state_values() -> None:
    assert [state.value for state in SessionState] == [
        "running",
        "done",
        "cancelled",
        "error",
        "interrupted",
    ]


def test_format_without_detail_is_one_line() -> None:
    assert format_status(SessionStatus(state=SessionState.DONE, detail="")) == "done\n"


def test_format_with_detail_puts_it_after_the_state() -> None:
    status = SessionStatus(state=SessionState.ERROR, detail="Market 1 does not cover the horizon")
    assert format_status(status) == "error\nMarket 1 does not cover the horizon\n"


@pytest.mark.parametrize(
    "status",
    [
        SessionStatus(state=SessionState.RUNNING, detail=""),
        SessionStatus(state=SessionState.ERROR, detail="line one\nline two"),
    ],
)
def test_parse_reads_format_back(status: SessionStatus) -> None:
    assert parse_status(format_status(status)) == status


def test_parse_rejects_unknown_state() -> None:
    with pytest.raises(ValueError):
        parse_status("paused\n")
