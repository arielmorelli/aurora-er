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
    RollingDispatchResultDTO,
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


def _shifted(result: DispatchResultDTO, hours: int) -> DispatchResultDTO:
    offset = timedelta(hours=hours)
    return dataclasses.replace(
        result,
        horizon=HorizonDTO(start=result.horizon.start + offset, end=result.horizon.end + offset),
    )


def _two_windows() -> RollingDispatchResultDTO:
    first = _two_hour_result()
    second = dataclasses.replace(
        _shifted(first, 2),
        status=SolveStatus.FEASIBLE,
        mip_gap=0.01,
        capex_gbp=0.0,
        opex_gbp=0.0,
        battery_value_start_gbp=2.0,
        battery_value_end_gbp=1.0,
        net_profit_gbp=39.0,
        replacements=1,
    )
    return RollingDispatchResultDTO(
        horizon=HorizonDTO(start=first.horizon.start, end=second.horizon.end),
        windows=(first, second),
    )


def test_rolling_totals_sum_the_windows() -> None:
    rolling = _two_windows()
    assert rolling.market_profit_gbp == 80.0
    assert rolling.capex_gbp == 10.0
    assert rolling.opex_gbp == 5.0
    assert rolling.net_profit_gbp == 24.0 + 39.0
    assert rolling.cycles_used_in_horizon == 2.0
    assert rolling.replacements == 1


def test_rolling_battery_values_come_from_the_ends() -> None:
    rolling = _two_windows()
    assert rolling.battery_value_start_gbp == 3.0
    assert rolling.battery_value_end_gbp == 1.0
    assert rolling.final_state == rolling.windows[-1].final_state


def test_rolling_is_optimal_only_if_every_window_is() -> None:
    assert not _two_windows().all_optimal
    single = _two_hour_result()
    assert RollingDispatchResultDTO(horizon=single.horizon, windows=(single,)).all_optimal


@pytest.mark.parametrize(
    ("windows", "message"),
    [
        ((), "must not be empty"),
        ((_shifted(_two_hour_result(), 1),), "first window"),
        ((_two_hour_result(), _shifted(_two_hour_result(), 3)), "last window|consecutive"),
    ],
)
def test_rolling_rejects_inconsistent_windows(
    windows: tuple[DispatchResultDTO, ...], message: str
) -> None:
    horizon = HorizonDTO(
        start=_two_hour_result().horizon.start,
        end=_two_hour_result().horizon.start + timedelta(hours=4),
    )
    with pytest.raises(InvalidDTOError, match=message):
        RollingDispatchResultDTO(horizon=horizon, windows=windows)


def test_rolling_rejects_gap_between_windows() -> None:
    first = _two_hour_result()
    later = _shifted(first, 3)
    with pytest.raises(InvalidDTOError, match="consecutive"):
        RollingDispatchResultDTO(
            horizon=HorizonDTO(start=first.horizon.start, end=later.horizon.end),
            windows=(first, later),
        )
