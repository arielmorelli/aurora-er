import dataclasses

import pytest

from aurora_er.dto import BatterySpecDTO


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
