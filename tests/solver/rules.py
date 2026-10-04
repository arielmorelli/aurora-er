"""Independent check that a dispatch result obeys the brief, recomputed from inputs."""

from collections.abc import Sequence

import pytest

from aurora_er.dto import BatteryDTO, DispatchResultDTO, MarketDTO
from aurora_er.timing import elapsed, in_hours

TOLERANCE = 1e-6


def assert_follows_brief(
    result: DispatchResultDTO, battery: BatteryDTO, markets: Sequence[MarketDTO]
) -> None:
    """Fail if `result` breaks a power, exclusivity, energy, degradation or revenue rule.

    Degradation is checked only when no battery was replaced in the horizon.
    """
    charge, discharge = _per_base_step(result)
    spec = battery.spec
    for charging, discharging in zip(charge, discharge, strict=True):
        assert charging <= spec.max_charging_rate_mw + TOLERANCE
        assert discharging <= spec.max_discharging_rate_mw + TOLERANCE
        assert charging <= TOLERANCE or discharging <= TOLERANCE

    base_hours = in_hours(result.energy_step_length)
    stored = result.stored_energy_mwh
    degradation_fraction = spec.degradation_rate_pct_per_cycle / 100
    cycles = battery.state.cycles_used
    assert stored[0] == pytest.approx(battery.state.stored_energy_mwh, abs=TOLERANCE)
    for step, (charging, discharging) in enumerate(zip(charge, discharge, strict=True)):
        expected = (
            stored[step]
            + base_hours * (1 - spec.charging_loss_fraction) * charging
            - base_hours * discharging / (1 - spec.discharging_loss_fraction)
        )
        assert stored[step + 1] == pytest.approx(expected, abs=TOLERANCE)
        cycles += (
            base_hours
            * discharging
            / (1 - spec.discharging_loss_fraction)
            / spec.max_storage_volume_mwh
        )
        usable_volume = spec.max_storage_volume_mwh * (1 - degradation_fraction * cycles)
        volume_limit = usable_volume if result.replacements == 0 else spec.max_storage_volume_mwh
        assert -TOLERANCE <= stored[step + 1] <= volume_limit + TOLERANCE

    for dispatch, market in zip(result.markets, markets, strict=True):
        first = elapsed(market.horizon_start, result.horizon.start) // market.step_length
        hours = in_hours(market.step_length)
        expected_profit = sum(
            hours
            * (
                market.sell_prices_gbp_per_mwh[first + index] * out
                - market.buy_prices_gbp_per_mwh[first + index] * into
            )
            for index, (into, out) in enumerate(
                zip(dispatch.charge_mw, dispatch.discharge_mw, strict=True)
            )
        )
        assert dispatch.profit_gbp == pytest.approx(expected_profit, abs=TOLERANCE)
    assert result.market_profit_gbp == pytest.approx(
        sum(dispatch.profit_gbp for dispatch in result.markets), abs=TOLERANCE
    )


def _per_base_step(result: DispatchResultDTO) -> tuple[list[float], list[float]]:
    step_count = len(result.stored_energy_mwh) - 1
    charge = [0.0] * step_count
    discharge = [0.0] * step_count
    for dispatch in result.markets:
        base_steps_per_interval = dispatch.step_length // result.energy_step_length
        for step in range(step_count):
            interval = step // base_steps_per_interval
            charge[step] += dispatch.charge_mw[interval]
            discharge[step] += dispatch.discharge_mw[interval]
    return charge, discharge
