from datetime import UTC, datetime, timedelta, timezone

import pytest

from aurora_er.sessions import created_at, new_session_id


def test_session_id_is_utc_time_to_the_microsecond() -> None:
    now = datetime(2026, 10, 4, 15, 30, 12, 123456, tzinfo=UTC)
    assert new_session_id(now) == "20261004T153012.123456Z"


def test_session_id_converts_to_utc() -> None:
    now = datetime(2026, 10, 4, 16, 30, 12, 5, tzinfo=timezone(timedelta(hours=1)))
    assert new_session_id(now) == "20261004T153012.000005Z"


def test_rejects_naive_time() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        new_session_id(datetime(2026, 10, 4))


def test_created_at_reads_the_id_back() -> None:
    now = datetime(2026, 10, 4, 15, 30, 12, 123456, tzinfo=UTC)
    assert created_at(new_session_id(now)) == now


def test_ids_sort_in_creation_order() -> None:
    earlier = new_session_id(datetime(2026, 10, 4, 9, 0, tzinfo=UTC))
    later = new_session_id(datetime(2026, 10, 4, 10, 0, tzinfo=UTC))
    assert sorted([later, earlier]) == [earlier, later]
