"""Battery parameters from a sheet laid out like `inputs/Attachment 1.xlsx`.

The sheet has one row per parameter: label in the first column, then `Values`
and `Units` columns. Labels are mapped to `BatterySpecDTO` fields, and units
are checked so a change of unit in the source fails loudly.
"""

import math
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from aurora_er.dto import BatterySpecDTO
from aurora_er.loading.errors import InputFileError

FIELDS_BY_LABEL = {
    "Max charging rate": ("max_charging_rate_mw", "MW"),
    "Max discharging rate": ("max_discharging_rate_mw", "MW"),
    "Max storage volume": ("max_storage_volume_mwh", "MWh"),
    "Battery charging efficiency": ("charging_loss_fraction", "-"),
    "Battery discharging efficiency": ("discharging_loss_fraction", "-"),
    "Lifetime (1)": ("lifetime_years", "years"),
    "Lifetime (2)": ("lifetime_cycles", "cycles"),
    "Storage volume degradation rate": ("degradation_rate_pct_per_cycle", "%/cycle"),
    "Capex": ("capex_gbp", "£"),
    "Fixed Operational Costs": ("fixed_operational_costs_gbp_per_year", "£/year"),
}
INTEGER_FIELDS = {"lifetime_years", "lifetime_cycles"}
VALUE_COLUMN = "Values"
UNIT_COLUMN = "Units"


@dataclass(frozen=True, slots=True, kw_only=True)
class BatterySheet:
    """Where the battery parameters are."""

    path: Path
    """Spreadsheet file."""

    sheet: str
    """Sheet name inside the file."""


def read_battery_spec(source: BatterySheet) -> BatterySpecDTO:
    """Read and convert the battery parameters sheet."""
    frame = pd.read_excel(source.path, sheet_name=source.sheet)
    return battery_spec_from_frame(frame)


def battery_spec_from_frame(frame: pd.DataFrame) -> BatterySpecDTO:
    """Convert a parameters table to `BatterySpecDTO`, checking labels and units."""
    _require_columns(frame)
    rows = frame.set_index(frame.columns[0])
    missing = [label for label in FIELDS_BY_LABEL if label not in rows.index]
    if missing:
        raise InputFileError(f"battery sheet is missing parameters: {', '.join(missing)}")
    values: dict[str, float | int] = {}
    for label, (field, unit) in FIELDS_BY_LABEL.items():
        found_unit = rows.at[label, UNIT_COLUMN]
        if found_unit != unit:
            raise InputFileError(f"'{label}' is in {found_unit!r}, expected {unit!r}")
        values[field] = _number(label, rows.at[label, VALUE_COLUMN], field in INTEGER_FIELDS)
    return BatterySpecDTO(**values)  # type: ignore[arg-type]


def _require_columns(frame: pd.DataFrame) -> None:
    for column in (VALUE_COLUMN, UNIT_COLUMN):
        if column not in frame.columns:
            raise InputFileError(f"battery sheet has no {column!r} column")


def _number(label: str, raw: object, integer: bool) -> float | int:
    try:
        value = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError) as error:
        raise InputFileError(f"'{label}' is not a number: {raw!r}") from error
    if not math.isfinite(value):
        raise InputFileError(f"'{label}' has no value")
    if not integer:
        return value
    if not value.is_integer():
        raise InputFileError(f"'{label}' must be a whole number, got {value}")
    return int(value)
