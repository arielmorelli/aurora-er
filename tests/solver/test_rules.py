import dataclasses
from typing import Any

import pytest

from aurora_er.dto import DispatchResultDTO, MarketDispatchDTO
from aurora_er.solver import HighsBackend, solve
from tests.solver.rules import assert_follows_brief
from tests.solver.scenarios import ONE_HOUR, battery, hours, market, options

BATTERY = battery()
MARKETS = [market("M", ONE_HOUR, (10, 50))]


def _solved() -> DispatchResultDTO:
    return solve(BATTERY, hours(2), MARKETS, options(), HighsBackend())


def _with_market(result: DispatchResultDTO, **changes: Any) -> DispatchResultDTO:
    return dataclasses.replace(result, markets=(dataclasses.replace(result.markets[0], **changes),))


def test_accepts_a_valid_dispatch() -> None:
    assert_follows_brief(_solved(), BATTERY, MARKETS)


def test_detects_power_above_rate() -> None:
    broken = _with_market(_solved(), charge_mw=(2.0, 0.0))
    with pytest.raises(AssertionError):
        assert_follows_brief(broken, BATTERY, MARKETS)


def test_detects_simultaneous_charge_and_discharge() -> None:
    broken = _with_market(_solved(), discharge_mw=(0.5, 1.0))
    with pytest.raises(AssertionError):
        assert_follows_brief(broken, BATTERY, MARKETS)


def test_detects_energy_imbalance() -> None:
    broken = dataclasses.replace(_solved(), stored_energy_mwh=(0.0, 0.5, 0.0))
    with pytest.raises(AssertionError):
        assert_follows_brief(broken, BATTERY, MARKETS)


def test_detects_wrong_market_profit() -> None:
    result = _solved()
    broken = dataclasses.replace(
        result,
        markets=(
            MarketDispatchDTO(
                name="M",
                step_length=ONE_HOUR,
                charge_mw=result.markets[0].charge_mw,
                discharge_mw=result.markets[0].discharge_mw,
                profit_gbp=41.0,
            ),
        ),
        market_profit_gbp=41.0,
        net_profit_gbp=41.0,
    )
    with pytest.raises(AssertionError):
        assert_follows_brief(broken, BATTERY, MARKETS)


def test_detects_energy_above_degraded_volume() -> None:
    degrading = battery(degradation_pct_per_cycle=10, lifetime_cycles=5)
    markets = [market("M", ONE_HOUR, (0, 10, 0, 10))]
    result = solve(degrading, hours(4), markets, options(), HighsBackend())
    assert result.stored_energy_mwh == pytest.approx((0, 1, 0, 0.9, 0))
    refilled_to_nominal = dataclasses.replace(
        _with_market(result, charge_mw=(1.0, 0.0, 1.0, 0.0), discharge_mw=(0.0, 1.0, 0.0, 1.0)),
        stored_energy_mwh=(0.0, 1.0, 0.0, 1.0, 0.0),
    )
    with pytest.raises(AssertionError):
        assert_follows_brief(refilled_to_nominal, degrading, markets)
