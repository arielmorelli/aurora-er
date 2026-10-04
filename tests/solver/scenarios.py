"""Builders for small, hand-checkable solver inputs."""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from aurora_er.dto import (
    BatteryDTO,
    BatterySpecDTO,
    BatteryStateDTO,
    HorizonDTO,
    MarketDTO,
    SolveOptionsDTO,
)
from aurora_er.timing import to_utc

START = datetime(2018, 1, 1, tzinfo=UTC)
LONG_AGO = datetime(2017, 6, 1, tzinfo=UTC)
ONE_HOUR = timedelta(hours=1)
HALF_HOUR = timedelta(minutes=30)


def battery(
    *,
    max_rate_mw: float = 1,
    volume_mwh: float = 1,
    charging_loss: float = 0,
    discharging_loss: float = 0,
    lifetime_years: int = 10,
    lifetime_cycles: int = 1000,
    degradation_pct_per_cycle: float = 0,
    capex_gbp: float = 0,
    opex_gbp_per_year: float = 0,
    stored_energy_mwh: float = 0,
    cycles_used: float = 0,
    commissioned_at: datetime = LONG_AGO,
) -> BatteryDTO:
    """A small battery, by default lossless, non-degrading and commissioned before `START`."""
    return BatteryDTO(
        spec=BatterySpecDTO(
            max_charging_rate_mw=max_rate_mw,
            max_discharging_rate_mw=max_rate_mw,
            max_storage_volume_mwh=volume_mwh,
            charging_loss_fraction=charging_loss,
            discharging_loss_fraction=discharging_loss,
            lifetime_years=lifetime_years,
            lifetime_cycles=lifetime_cycles,
            degradation_rate_pct_per_cycle=degradation_pct_per_cycle,
            capex_gbp=capex_gbp,
            fixed_operational_costs_gbp_per_year=opex_gbp_per_year,
        ),
        state=BatteryStateDTO(
            stored_energy_mwh=stored_energy_mwh,
            cycles_used=cycles_used,
            commissioned_at=commissioned_at,
        ),
    )


def market(
    name: str,
    step_length: timedelta,
    prices: Sequence[float],
    *,
    start: datetime = START,
    sell_prices: Sequence[float] | None = None,
) -> MarketDTO:
    """A market starting at `start`; sell prices default to the buy prices."""
    return MarketDTO(
        name=name,
        horizon_start=start,
        horizon_end=(to_utc(start) + len(prices) * step_length).astimezone(start.tzinfo),
        step_length=step_length,
        buy_prices_gbp_per_mwh=tuple(prices),
        sell_prices_gbp_per_mwh=tuple(prices if sell_prices is None else sell_prices),
    )


def hours(count: float, *, start: datetime = START) -> HorizonDTO:
    """Horizon of `count` real hours from `start`."""
    return HorizonDTO(start=start, end=(to_utc(start) + count * ONE_HOUR).astimezone(start.tzinfo))


def options(*, enforce_cycle_pace: bool = False) -> SolveOptionsDTO:
    """Exact solve with a generous time limit."""
    return SolveOptionsDTO(enforce_cycle_pace=enforce_cycle_pace, time_limit_seconds=30, mip_gap=0)
