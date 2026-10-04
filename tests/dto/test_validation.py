import math
from datetime import UTC, datetime, timedelta, timezone, tzinfo

import pytest

from aurora_er.dto.validation import InvalidDTOError, are_finite, is_timezone_aware, require


class _OffsetlessZone(tzinfo):
    def utcoffset(self, dt: datetime | None) -> timedelta | None:
        return None

    def dst(self, dt: datetime | None) -> timedelta | None:
        return None

    def tzname(self, dt: datetime | None) -> str | None:
        return None


def test_require_passes_when_condition_holds() -> None:
    require(True, "unused")


def test_require_raises_with_message_when_condition_fails() -> None:
    with pytest.raises(InvalidDTOError, match="must be positive"):
        require(False, "must be positive")


def test_invalid_dto_error_is_a_value_error() -> None:
    assert issubclass(InvalidDTOError, ValueError)


@pytest.mark.parametrize(
    "moment",
    [
        datetime(2018, 1, 1, tzinfo=UTC),
        datetime(2018, 1, 1, tzinfo=timezone(timedelta(hours=1))),
    ],
)
def test_is_timezone_aware_accepts_aware_datetimes(moment: datetime) -> None:
    assert is_timezone_aware(moment)


@pytest.mark.parametrize(
    "moment",
    [
        datetime(2018, 1, 1),
        datetime(2018, 1, 1, tzinfo=_OffsetlessZone()),
    ],
)
def test_is_timezone_aware_rejects_naive_datetimes(moment: datetime) -> None:
    assert not is_timezone_aware(moment)


def test_are_finite_accepts_finite_values_including_negative() -> None:
    assert are_finite((-68.5, 0.0, 494.4))


def test_are_finite_accepts_empty() -> None:
    assert are_finite(())


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_are_finite_rejects_non_finite_values(bad: float) -> None:
    assert not are_finite((1.0, bad))
