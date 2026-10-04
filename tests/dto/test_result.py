import dataclasses
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from aurora_er.dto import (
    BatteryStateDTO,
    DispatchResultDTO,
    HorizonDTO,
    InvalidDTOError,
    MarketDispatchDTO,
    SolveStatus,
)


def _charge_then_discharge() -> MarketDispatchDTO:
    return MarketDispatchDTO(
        name="Market 2",
        step_length=timedelta(hours=1),
        charge_mw=(1.0, 0.0),
        discharge_mw=(0.0, 1.0),
        profit_gbp=40.0,
    )


def _two_hour_result() -> DispatchResultDTO:
    return DispatchResultDTO(
        horizon=HorizonDTO(
            start=datetime(2018, 1, 1, tzinfo=UTC), end=datetime(2018, 1, 1, 2, tzinfo=UTC)
        ),
        status=SolveStatus.OPTIMAL,
        mip_gap=0.0,
        market_profit_gbp=40.0,
        capex_gbp=10.0,
        opex_gbp=5.0,
        battery_value_start_gbp=3.0,
        battery_value_end_gbp=2.0,
        net_profit_gbp=24.0,
        markets=(_charge_then_discharge(),),
        energy_step_length=timedelta(hours=1),
        stored_energy_mwh=(0.0, 1.0, 0.0),
        cycles_used_in_horizon=1.0,
        replacements=0,
        final_state=BatteryStateDTO(
            stored_energy_mwh=0.0, cycles_used=1.0, commissioned_at=datetime(2018, 1, 1, tzinfo=UTC)
        ),
    )


def test_status_values() -> None:
    assert SolveStatus.OPTIMAL.value == "optimal"
    assert SolveStatus.FEASIBLE.value == "feasible"


def test_market_dispatch_is_valid() -> None:
    assert _charge_then_discharge().profit_gbp == 40.0


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"name": ""}, "name"),
        ({"step_length": timedelta(0)}, "step_length"),
        ({"charge_mw": (1.0,)}, "same length"),
        ({"charge_mw": (-0.1, 0.0)}, "must not be negative"),
        ({"discharge_mw": (0.0, -0.1)}, "must not be negative"),
        ({"profit_gbp": float("nan")}, "finite"),
    ],
)
def test_market_dispatch_rejects_invalid_values(changes: dict[str, Any], message: str) -> None:
    with pytest.raises(InvalidDTOError, match=message):
        dataclasses.replace(_charge_then_discharge(), **changes)


def test_result_is_valid() -> None:
    assert _two_hour_result().net_profit_gbp == 40.0 - 10.0 - 5.0 + 2.0 - 3.0


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"mip_gap": -0.1}, "mip_gap"),
        ({"capex_gbp": -1.0, "net_profit_gbp": 35.0}, "capex_gbp"),
        ({"opex_gbp": -1.0, "net_profit_gbp": 30.0}, "opex_gbp"),
        ({"battery_value_start_gbp": -1.0, "net_profit_gbp": 28.0}, "battery_value_start"),
        ({"battery_value_end_gbp": -1.0, "net_profit_gbp": 21.0}, "battery_value_end"),
        ({"net_profit_gbp": 25.0}, "net_profit_gbp must equal"),
        ({"market_profit_gbp": float("inf")}, "finite"),
        ({"markets": ()}, "markets"),
        ({"energy_step_length": timedelta(0)}, "energy_step_length"),
        ({"stored_energy_mwh": (0.0,)}, "cover the horizon"),
        ({"stored_energy_mwh": (0.0, -0.1, 0.0)}, "stored_energy_mwh must not be negative"),
        ({"cycles_used_in_horizon": -1.0}, "cycles_used_in_horizon"),
        ({"replacements": -1}, "replacements"),
    ],
)
def test_result_rejects_invalid_values(changes: dict[str, Any], message: str) -> None:
    with pytest.raises(InvalidDTOError, match=message):
        dataclasses.replace(_two_hour_result(), **changes)
