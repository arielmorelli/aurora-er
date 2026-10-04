"""Numeric problem data derived from the input DTOs, ready to build the model from."""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from aurora_er.dto import BatteryDTO, BatterySpecDTO, HorizonDTO, MarketDTO, SolveOptionsDTO
from aurora_er.timing import add_years, elapsed, in_hours, to_utc


@dataclass(frozen=True, slots=True, kw_only=True)
class PreparedMarket:
    """A market's prices restricted to the horizon, mapped onto the base grid."""

    name: str
    """Market identifier."""

    step_length: timedelta
    """Duration of one market interval."""

    base_steps_per_interval: int
    """How many base steps one market interval spans."""

    buy_prices_gbp_per_mwh: tuple[float, ...]
    """Buy price per market interval within the horizon."""

    sell_prices_gbp_per_mwh: tuple[float, ...]
    """Sell price per market interval within the horizon."""

    @property
    def interval_count(self) -> int:
        """Number of market intervals in the horizon."""
        return len(self.buy_prices_gbp_per_mwh)

    @property
    def interval_hours(self) -> float:
        """Duration of one market interval in hours."""
        return in_hours(self.step_length)

    def interval_of(self, base_step: int) -> int:
        """Index of the market interval containing ``base_step``."""
        return base_step // self.base_steps_per_interval


@dataclass(frozen=True, slots=True, kw_only=True)
class DispatchProblem:
    """Everything the model needs, with time already discretised."""

    battery: BatteryDTO
    """Battery specification and initial state."""

    horizon: HorizonDTO
    """Window being optimised."""

    base_step: timedelta
    """Finest market step; the grid on which energy is tracked."""

    base_step_count: int
    """Number of base steps in the horizon."""

    markets: tuple[PreparedMarket, ...]
    """Markets in input order."""

    calendar_end_boundary: int | None
    """Base-step boundary at which the initial battery reaches its calendar life, if in horizon."""

    replacement_bound: int
    """Upper bound on cycle-driven replacements in the horizon."""

    cycle_cap: float | None
    """Maximum cycles in the horizon when cycle pace is enforced, else ``None``."""

    initial_capex_gbp: float
    """Purchase cost if the battery is commissioned at the horizon start, else 0."""

    opex_gbp: float
    """Fixed operational costs for operating years started in the horizon."""

    battery_value_start_gbp: float
    """Value of the battery owned before the horizon; 0 if bought at its start."""

    @property
    def base_step_hours(self) -> float:
        """Duration of one base step in hours."""
        return in_hours(self.base_step)

    def boundary_time(self, boundary: int) -> datetime:
        """Instant of a base-step boundary, in the horizon's timezone."""
        return (to_utc(self.horizon.start) + boundary * self.base_step).astimezone(
            self.horizon.start.tzinfo
        )


def prepare_problem(
    battery: BatteryDTO,
    horizon: HorizonDTO,
    markets: Sequence[MarketDTO],
    options: SolveOptionsDTO,
) -> DispatchProblem:
    """Discretise validated inputs onto the base grid and derive the model constants."""
    base_step = min(market.step_length for market in markets)
    base_step_count = horizon.length // base_step
    return DispatchProblem(
        battery=battery,
        horizon=horizon,
        base_step=base_step,
        base_step_count=base_step_count,
        markets=tuple(_prepare_market(market, horizon, base_step) for market in markets),
        calendar_end_boundary=calendar_end_boundary(battery, horizon, base_step),
        replacement_bound=replacement_bound(battery, base_step_count * base_step),
        cycle_cap=cycle_cap(battery, horizon) if options.enforce_cycle_pace else None,
        initial_capex_gbp=initial_capex_gbp(battery, horizon),
        opex_gbp=opex_gbp(battery, horizon),
        battery_value_start_gbp=battery_value_start_gbp(battery, horizon),
    )


def _prepare_market(market: MarketDTO, horizon: HorizonDTO, base_step: timedelta) -> PreparedMarket:
    first = elapsed(market.horizon_start, horizon.start) // market.step_length
    count = horizon.length // market.step_length
    return PreparedMarket(
        name=market.name,
        step_length=market.step_length,
        base_steps_per_interval=market.step_length // base_step,
        buy_prices_gbp_per_mwh=market.buy_prices_gbp_per_mwh[first : first + count],
        sell_prices_gbp_per_mwh=market.sell_prices_gbp_per_mwh[first : first + count],
    )


def calendar_end_of_life(battery: BatteryDTO) -> datetime:
    """When the installed battery reaches ``lifetime_years``."""
    return add_years(battery.state.commissioned_at, battery.spec.lifetime_years)


def calendar_end_boundary(
    battery: BatteryDTO, horizon: HorizonDTO, base_step: timedelta
) -> int | None:
    """First base-step boundary at or after the calendar end of life, if strictly inside."""
    end_of_life = calendar_end_of_life(battery)
    if not to_utc(horizon.start) < to_utc(end_of_life) < to_utc(horizon.end):
        return None
    return -(-elapsed(horizon.start, end_of_life) // base_step)


def replacement_bound(battery: BatteryDTO, duration: timedelta) -> int:
    """Most cycle-driven replacements physically possible within ``duration``."""
    spec = battery.spec
    max_drained_mwh = (
        in_hours(duration) * spec.max_discharging_rate_mw / (1 - spec.discharging_loss_fraction)
    )
    max_cycles = battery.state.cycles_used + max_drained_mwh / spec.max_storage_volume_mwh
    return max(1, math.ceil(max_cycles / spec.lifetime_cycles))


def cycle_cap(battery: BatteryDTO, horizon: HorizonDTO) -> float:
    """Remaining cycles spread evenly over the remaining calendar life, for the horizon."""
    remaining_cycles = battery.spec.lifetime_cycles - battery.state.cycles_used
    remaining_life = elapsed(horizon.start, calendar_end_of_life(battery))
    return remaining_cycles * (horizon.length / remaining_life)


def battery_value_gbp(spec: BatterySpecDTO, cycles_used: Any) -> Any:
    """Capex in proportion to the cycles the battery has left.

    Linear in ``cycles_used``, so it also accepts a model expression.
    """
    return spec.capex_gbp * (spec.lifetime_cycles - cycles_used) / spec.lifetime_cycles


def battery_value_start_gbp(battery: BatteryDTO, horizon: HorizonDTO) -> float:
    """Value of the battery owned before the horizon; 0 when it is bought at the start."""
    if initial_capex_gbp(battery, horizon) > 0:
        return 0.0
    value: float = battery_value_gbp(battery.spec, battery.state.cycles_used)
    return value


def initial_capex_gbp(battery: BatteryDTO, horizon: HorizonDTO) -> float:
    """The purchase cost when the battery is commissioned at the horizon start."""
    if to_utc(battery.state.commissioned_at) == to_utc(horizon.start):
        return battery.spec.capex_gbp
    return 0.0


def opex_gbp(battery: BatteryDTO, horizon: HorizonDTO) -> float:
    """Fixed costs for each operating year (from commissioning) starting in the horizon."""
    years_started = 0
    year = 0
    anniversary = battery.state.commissioned_at
    while to_utc(anniversary) < to_utc(horizon.end):
        if to_utc(anniversary) >= to_utc(horizon.start):
            years_started += 1
        year += 1
        anniversary = add_years(battery.state.commissioned_at, year)
    return years_started * battery.spec.fixed_operational_costs_gbp_per_year
