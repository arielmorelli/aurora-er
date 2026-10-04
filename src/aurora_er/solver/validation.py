"""Checks that span several input DTOs, run before building the model."""

from collections.abc import Sequence
from datetime import timedelta

from aurora_er.dto import BatteryDTO, HorizonDTO, MarketDTO
from aurora_er.solver.errors import InvalidSolveInputError
from aurora_er.timing import add_years, elapsed, to_utc


def validate_inputs(battery: BatteryDTO, horizon: HorizonDTO, markets: Sequence[MarketDTO]) -> None:
    """Raise `InvalidSolveInputError` if the inputs cannot be solved together."""
    _validate_markets(horizon, markets)
    _validate_battery_lifetime(battery, horizon)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidSolveInputError(message)


def _validate_markets(horizon: HorizonDTO, markets: Sequence[MarketDTO]) -> None:
    _require(bool(markets), "at least one market is required")
    names = [market.name for market in markets]
    _require(len(names) == len(set(names)), "market names must be unique")
    finest_step = min(market.step_length for market in markets)
    for market in markets:
        _require(
            to_utc(market.horizon_start) <= to_utc(horizon.start)
            and to_utc(horizon.end) <= to_utc(market.horizon_end),
            f"{market.name} does not cover the horizon",
        )
        _require(
            _is_on_grid(market, elapsed(market.horizon_start, horizon.start))
            and _is_on_grid(market, elapsed(market.horizon_start, horizon.end)),
            f"horizon does not align with the intervals of {market.name}",
        )
        _require(
            market.step_length % finest_step == timedelta(0),
            f"step_length of {market.name} is not a whole multiple of the finest step",
        )


def _is_on_grid(market: MarketDTO, offset: timedelta) -> bool:
    return offset % market.step_length == timedelta(0)


def _validate_battery_lifetime(battery: BatteryDTO, horizon: HorizonDTO) -> None:
    lifetime_years = battery.spec.lifetime_years
    commissioned_at = to_utc(battery.state.commissioned_at)
    end_of_life = to_utc(add_years(battery.state.commissioned_at, lifetime_years))
    _require(
        to_utc(horizon.end) <= to_utc(add_years(horizon.start, lifetime_years)),
        "horizon must not be longer than lifetime_years",
    )
    _require(
        commissioned_at <= to_utc(horizon.start), "battery must be commissioned by horizon start"
    )
    _require(
        to_utc(horizon.start) < end_of_life, "battery is past its calendar life at horizon start"
    )
