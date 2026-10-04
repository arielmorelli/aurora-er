from pathlib import Path

import pandas as pd
import pytest

from aurora_er.loading import (
    BatterySheet,
    InputFileError,
    battery_spec_from_frame,
    read_battery_spec,
)

ATTACHMENT_1 = Path(__file__).parents[2] / "inputs" / "Attachment 1.xlsx"

ATTACHMENT_1_ROWS: list[tuple[str, object, str]] = [
    ("Max charging rate", 2, "MW"),
    ("Max discharging rate", 2, "MW"),
    ("Max storage volume", 4, "MWh"),
    ("Battery charging efficiency", 0.05, "-"),
    ("Battery discharging efficiency", 0.05, "-"),
    ("Lifetime (1)", 10, "years"),
    ("Lifetime (2)", 5000, "cycles"),
    ("Storage volume degradation rate", 0.001, "%/cycle"),
    ("Capex", 500000, "£"),
    ("Fixed Operational Costs", 5000, "£/year"),
]


def _attachment_1_frame(rows: list[tuple[str, object, str]] = ATTACHMENT_1_ROWS) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["Parameter", "Values", "Units"])


def _replace_row(label: str, value: object, unit: str) -> list[tuple[str, object, str]]:
    return [(label, value, unit) if row[0] == label else row for row in ATTACHMENT_1_ROWS]


def test_maps_every_parameter_to_its_field() -> None:
    spec = battery_spec_from_frame(_attachment_1_frame())
    assert spec.max_charging_rate_mw == 2
    assert spec.max_discharging_rate_mw == 2
    assert spec.max_storage_volume_mwh == 4
    assert spec.charging_loss_fraction == 0.05
    assert spec.discharging_loss_fraction == 0.05
    assert spec.lifetime_years == 10
    assert spec.lifetime_cycles == 5000
    assert spec.degradation_rate_pct_per_cycle == 0.001
    assert spec.capex_gbp == 500_000
    assert spec.fixed_operational_costs_gbp_per_year == 5_000


def test_lifetimes_are_integers() -> None:
    spec = battery_spec_from_frame(_attachment_1_frame())
    assert isinstance(spec.lifetime_years, int)
    assert isinstance(spec.lifetime_cycles, int)


def test_rejects_missing_parameter() -> None:
    with pytest.raises(InputFileError, match="Capex"):
        battery_spec_from_frame(
            _attachment_1_frame([r for r in ATTACHMENT_1_ROWS if r[0] != "Capex"])
        )


def test_rejects_unexpected_unit() -> None:
    with pytest.raises(InputFileError, match="'Max storage volume' is in 'kWh'"):
        battery_spec_from_frame(_attachment_1_frame(_replace_row("Max storage volume", 4, "kWh")))


def test_rejects_non_numeric_value() -> None:
    with pytest.raises(InputFileError, match="not a number"):
        battery_spec_from_frame(_attachment_1_frame(_replace_row("Capex", "lots", "£")))


def test_rejects_empty_value() -> None:
    with pytest.raises(InputFileError, match="'Capex' has no value"):
        battery_spec_from_frame(_attachment_1_frame(_replace_row("Capex", None, "£")))


def test_rejects_fractional_lifetime() -> None:
    with pytest.raises(InputFileError, match="whole number"):
        battery_spec_from_frame(_attachment_1_frame(_replace_row("Lifetime (1)", 10.5, "years")))


def test_rejects_missing_column() -> None:
    with pytest.raises(InputFileError, match="'Units'"):
        battery_spec_from_frame(_attachment_1_frame().drop(columns=["Units"]))


def test_reads_spreadsheet_file(tmp_path: Path) -> None:
    path = tmp_path / "battery.xlsx"
    _attachment_1_frame().to_excel(path, sheet_name="Data", index=False)
    assert read_battery_spec(BatterySheet(path=path, sheet="Data")).capex_gbp == 500_000


def test_reads_the_provided_attachment() -> None:
    spec = read_battery_spec(BatterySheet(path=ATTACHMENT_1, sheet="Data"))
    assert spec == battery_spec_from_frame(_attachment_1_frame())
