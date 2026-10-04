import dataclasses
from datetime import UTC, datetime
from typing import Any

import pytest

from aurora_er.dto import BatteryDTO, BatterySpecDTO, BatteryStateDTO, InvalidDTOError


def _attachment_1_spec() -> BatterySpecDTO:
    return BatterySpecDTO(
        max_charging_rate_mw=2,
        max_discharging_rate_mw=2,
        max_storage_volume_mwh=4,
        charging_loss_fraction=0.05,
        discharging_loss_fraction=0.05,
        lifetime_years=10,
        lifetime_cycles=5000,
        degradation_rate_pct_per_cycle=0.001,
        capex_gbp=500_000,
        fixed_operational_costs_gbp_per_year=5_000,
    )


def test_is_immutable() -> None:
    spec = _attachment_1_spec()
    with pytest.raises(dataclasses.FrozenInstanceError):
        spec.max_storage_volume_mwh = 8  # type: ignore[misc]


def test_requires_keyword_arguments() -> None:
    with pytest.raises(TypeError):
        BatterySpecDTO(2, 2, 4, 0.05, 0.05, 10, 5000, 0.001, 500_000, 5_000)  # type: ignore[call-arg]


def test_equal_when_fields_equal() -> None:
    assert _attachment_1_spec() == _attachment_1_spec()
    assert hash(_attachment_1_spec()) == hash(_attachment_1_spec())


def test_replace_returns_new_instance() -> None:
    spec = _attachment_1_spec()
    bigger = dataclasses.replace(spec, max_storage_volume_mwh=8)
    assert bigger.max_storage_volume_mwh == 8
    assert spec.max_storage_volume_mwh == 4


def test_accepts_attachment_1_values() -> None:
    assert _attachment_1_spec().max_storage_volume_mwh == 4


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"max_charging_rate_mw": 0}, "max_charging_rate_mw"),
        ({"max_discharging_rate_mw": -1}, "max_discharging_rate_mw"),
        ({"max_storage_volume_mwh": 0}, "max_storage_volume_mwh"),
        ({"charging_loss_fraction": -0.01}, "charging_loss_fraction"),
        ({"charging_loss_fraction": 1}, "charging_loss_fraction"),
        ({"discharging_loss_fraction": -0.01}, "discharging_loss_fraction"),
        ({"discharging_loss_fraction": 1}, "discharging_loss_fraction"),
        ({"lifetime_years": 0}, "lifetime_years"),
        ({"lifetime_cycles": 0}, "lifetime_cycles"),
        ({"degradation_rate_pct_per_cycle": -0.001}, "degradation_rate_pct_per_cycle"),
        ({"degradation_rate_pct_per_cycle": 0.02}, "usable volume"),
        ({"capex_gbp": -1}, "capex_gbp"),
        ({"fixed_operational_costs_gbp_per_year": -1}, "fixed_operational_costs"),
    ],
)
def test_rejects_invalid_values(changes: dict[str, Any], message: str) -> None:
    with pytest.raises(InvalidDTOError, match=message):
        dataclasses.replace(_attachment_1_spec(), **changes)


def _new_empty_state() -> BatteryStateDTO:
    return BatteryStateDTO(
        stored_energy_mwh=0, cycles_used=0, commissioned_at=datetime(2018, 1, 1, tzinfo=UTC)
    )


def _new_empty_battery() -> BatteryDTO:
    return BatteryDTO(spec=_attachment_1_spec(), state=_new_empty_state())


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"stored_energy_mwh": -0.1}, "stored_energy_mwh"),
        ({"stored_energy_mwh": float("nan")}, "finite"),
        ({"cycles_used": -1}, "cycles_used"),
        ({"cycles_used": float("inf")}, "finite"),
        ({"commissioned_at": datetime(2018, 1, 1)}, "commissioned_at must be timezone-aware"),
    ],
)
def test_state_rejects_invalid_values(changes: dict[str, Any], message: str) -> None:
    with pytest.raises(InvalidDTOError, match=message):
        dataclasses.replace(_new_empty_state(), **changes)


def test_usable_volume_of_new_battery_is_nominal() -> None:
    assert _new_empty_battery().usable_volume_mwh == 4


def test_usable_volume_shrinks_with_cycles_used() -> None:
    worn_state = dataclasses.replace(_new_empty_state(), cycles_used=1000)
    battery = dataclasses.replace(_new_empty_battery(), state=worn_state)
    assert battery.usable_volume_mwh == pytest.approx(4 * (1 - 0.00001 * 1000))


def test_battery_accepts_full_usable_volume() -> None:
    full = dataclasses.replace(_new_empty_state(), stored_energy_mwh=4)
    assert dataclasses.replace(_new_empty_battery(), state=full).state.stored_energy_mwh == 4


def test_battery_rejects_energy_above_usable_volume() -> None:
    worn_and_full = dataclasses.replace(_new_empty_state(), cycles_used=1000, stored_energy_mwh=4)
    with pytest.raises(InvalidDTOError, match="usable volume"):
        dataclasses.replace(_new_empty_battery(), state=worn_and_full)


def test_battery_rejects_cycles_beyond_lifetime() -> None:
    exhausted = dataclasses.replace(_new_empty_state(), cycles_used=5001)
    with pytest.raises(InvalidDTOError, match="lifetime_cycles"):
        dataclasses.replace(_new_empty_battery(), state=exhausted)
