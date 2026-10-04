from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from aurora_er.dto import DispatchResultDTO, HorizonDTO
from aurora_er.solver import HighsBackend, monthly_windows, solve_rolling
from tests.solver.scenarios import ONE_HOUR, START, battery, hours, market, options


def _utc(year: int, month: int, day: int = 1) -> datetime:
    return datetime(year, month, day, tzinfo=UTC)


def _bounds(windows: tuple[HorizonDTO, ...]) -> list[tuple[datetime, datetime]]:
    return [(window.start, window.end) for window in windows]


def test_monthly_windows_split_at_month_starts() -> None:
    windows = monthly_windows(HorizonDTO(start=_utc(2018, 1), end=_utc(2018, 4)), 1)
    assert _bounds(windows) == [
        (_utc(2018, 1), _utc(2018, 2)),
        (_utc(2018, 2), _utc(2018, 3)),
        (_utc(2018, 3), _utc(2018, 4)),
    ]


def test_monthly_windows_keep_partial_first_and_last_months() -> None:
    windows = monthly_windows(HorizonDTO(start=_utc(2018, 1, 15), end=_utc(2018, 3, 10)), 1)
    assert _bounds(windows) == [
        (_utc(2018, 1, 15), _utc(2018, 2)),
        (_utc(2018, 2), _utc(2018, 3)),
        (_utc(2018, 3), _utc(2018, 3, 10)),
    ]


def test_monthly_windows_group_several_months() -> None:
    windows = monthly_windows(HorizonDTO(start=_utc(2018, 1), end=_utc(2018, 6)), 2)
    assert _bounds(windows) == [
        (_utc(2018, 1), _utc(2018, 3)),
        (_utc(2018, 3), _utc(2018, 5)),
        (_utc(2018, 5), _utc(2018, 6)),
    ]


def test_monthly_windows_follow_local_months() -> None:
    london = ZoneInfo("Europe/London")
    horizon = HorizonDTO(
        start=datetime(2018, 3, 1, tzinfo=london), end=datetime(2018, 5, 1, tzinfo=london)
    )
    assert monthly_windows(horizon, 1)[1].start == datetime(2018, 4, 1, tzinfo=london)


def test_monthly_windows_short_horizon_is_one_window() -> None:
    assert _bounds(monthly_windows(hours(4), 1)) == [(START, START + 4 * ONE_HOUR)]


def test_monthly_windows_reject_zero_months() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        monthly_windows(hours(4), 0)


def test_solve_rolling_chains_state_between_windows() -> None:
    worn = battery(capex_gbp=100, lifetime_cycles=100)
    windows = (hours(2), hours(2, start=START + 2 * ONE_HOUR))
    solved: list[DispatchResultDTO] = []
    result = solve_rolling(
        worn,
        windows,
        [market("M", ONE_HOUR, (0, 10, 0, 10))],
        options(),
        HighsBackend(),
        solved.append,
    )
    first, second = result.windows
    assert solved == [first, second]
    assert second.battery_value_start_gbp == pytest.approx(first.battery_value_end_gbp)
    assert result.final_state.cycles_used == pytest.approx(2)
    assert result.market_profit_gbp == pytest.approx(20)
    assert result.net_profit_gbp == pytest.approx(first.net_profit_gbp + second.net_profit_gbp)
    assert result.horizon == HorizonDTO(start=START, end=START + 4 * ONE_HOUR)
