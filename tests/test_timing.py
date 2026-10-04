from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from aurora_er.timing import add_years, elapsed, in_hours, to_utc

LONDON = ZoneInfo("Europe/London")


def test_to_utc_converts_offset() -> None:
    summer = datetime(2018, 7, 1, 12, 0, tzinfo=LONDON)
    assert to_utc(summer) == datetime(2018, 7, 1, 11, 0, tzinfo=UTC)
    assert to_utc(summer).tzinfo is UTC


def test_elapsed_in_utc() -> None:
    assert elapsed(
        datetime(2018, 1, 1, tzinfo=UTC), datetime(2018, 1, 1, 3, tzinfo=UTC)
    ) == timedelta(hours=3)


def test_elapsed_counts_real_time_when_clocks_go_forward() -> None:
    assert elapsed(
        datetime(2018, 3, 25, 0, 0, tzinfo=LONDON), datetime(2018, 3, 25, 3, 0, tzinfo=LONDON)
    ) == timedelta(hours=2)


def test_elapsed_counts_real_time_when_clocks_go_back() -> None:
    assert elapsed(
        datetime(2018, 10, 28, 0, 0, tzinfo=LONDON), datetime(2018, 10, 28, 3, 0, tzinfo=LONDON)
    ) == timedelta(hours=4)


def test_elapsed_across_timezones() -> None:
    assert elapsed(
        datetime(2018, 7, 1, 12, 0, tzinfo=LONDON), datetime(2018, 7, 1, 12, 0, tzinfo=UTC)
    ) == timedelta(hours=1)


def test_in_hours() -> None:
    assert in_hours(timedelta(minutes=30)) == 0.5
    assert in_hours(timedelta(days=1)) == 24


def test_add_years_keeps_wall_clock_time_and_zone() -> None:
    moment = datetime(2018, 1, 1, 6, 30, tzinfo=LONDON)
    assert add_years(moment, 10) == datetime(2028, 1, 1, 6, 30, tzinfo=LONDON)


def test_add_years_maps_29_february_to_28_february() -> None:
    assert add_years(datetime(2020, 2, 29, tzinfo=UTC), 1) == datetime(2021, 2, 28, tzinfo=UTC)


def test_add_years_keeps_29_february_in_leap_years() -> None:
    assert add_years(datetime(2020, 2, 29, tzinfo=UTC), 4) == datetime(2024, 2, 29, tzinfo=UTC)
