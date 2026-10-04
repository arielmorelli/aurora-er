"""Long horizons solved as consecutive windows of a day, a week or a month."""

import dataclasses
from collections.abc import Callable, Sequence
from datetime import timedelta
from enum import StrEnum

from aurora_er.dto import (
    BatteryDTO,
    DispatchResultDTO,
    HorizonDTO,
    MarketDTO,
    RollingDispatchResultDTO,
    SolveOptionsDTO,
)
from aurora_er.solver.backend import MilpBackend
from aurora_er.solver.solve import solve
from aurora_er.timing import add_months, to_utc


class WindowSize(StrEnum):
    """How much of the horizon is solved at once."""

    DAY = "day"
    """24 hours from the horizon start."""

    WEEK = "week"
    """7 days from the horizon start."""

    MONTH = "month"
    """A calendar month."""


def rolling_windows(horizon: HorizonDTO, size: WindowSize) -> tuple[HorizonDTO, ...]:
    """Split `horizon` into consecutive windows of `size`; the last one may be shorter."""
    match size:
        case WindowSize.DAY:
            return fixed_windows(horizon, timedelta(days=1))
        case WindowSize.WEEK:
            return fixed_windows(horizon, timedelta(weeks=1))
        case WindowSize.MONTH:
            return monthly_windows(horizon, 1)


def fixed_windows(horizon: HorizonDTO, length: timedelta) -> tuple[HorizonDTO, ...]:
    """Split `horizon` into windows of `length` real time from its start."""
    if length <= timedelta(0):
        raise ValueError("length must be positive")
    windows = []
    start_utc = to_utc(horizon.start)
    end_utc = to_utc(horizon.end)
    while start_utc < end_utc:
        window_end_utc = min(start_utc + length, end_utc)
        windows.append(
            HorizonDTO(
                start=start_utc.astimezone(horizon.start.tzinfo),
                end=window_end_utc.astimezone(horizon.start.tzinfo),
            )
        )
        start_utc = window_end_utc
    return tuple(windows)


def monthly_windows(horizon: HorizonDTO, months_per_window: int) -> tuple[HorizonDTO, ...]:
    """Split `horizon` at calendar-month boundaries in its start's timezone.

    Windows start on the 1st of a month; the first and last may be partial.
    """
    if months_per_window < 1:
        raise ValueError("months_per_window must be at least 1")
    first_month = horizon.start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    windows = []
    start = horizon.start
    step = 1
    while to_utc(start) < to_utc(horizon.end):
        boundary = add_months(first_month, step * months_per_window)
        end = boundary if to_utc(boundary) < to_utc(horizon.end) else horizon.end
        windows.append(HorizonDTO(start=start, end=end))
        start = end
        step += 1
    return tuple(windows)


def solve_rolling(
    battery: BatteryDTO,
    windows: Sequence[HorizonDTO],
    markets: Sequence[MarketDTO],
    options: SolveOptionsDTO,
    backend: MilpBackend,
    on_window_solved: Callable[[DispatchResultDTO], None],
) -> RollingDispatchResultDTO:
    """Solve each window in turn, starting each from the previous window's final state.

    `on_window_solved` is called after every window, e.g. to report progress.
    """
    results = []
    current = battery
    for window in windows:
        result = solve(current, window, markets, options, backend)
        on_window_solved(result)
        results.append(result)
        current = dataclasses.replace(current, state=result.final_state)
    return RollingDispatchResultDTO(
        horizon=HorizonDTO(start=windows[0].start, end=windows[-1].end),
        windows=tuple(results),
    )
