"""Battery technical and financial parameters, as provided in ``docs/input/Attachment 1.xlsx``."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class BatterySpecDTO:
    """Battery parameters. Field names carry their unit as a suffix."""

    max_charging_rate_mw: float
    """Maximum power the battery can import from the grid."""

    max_discharging_rate_mw: float
    """Maximum power the battery can export to the grid."""

    max_storage_volume_mwh: float
    """Maximum volume of energy the battery can store."""

    charging_loss_fraction: float
    """Fraction of energy imported from the grid lost before storage.

    Labelled "Battery charging efficiency" in the source, but the value is a loss.
    """

    discharging_loss_fraction: float
    """Fraction of energy exported from the battery lost before reaching the grid.

    Labelled "Battery discharging efficiency" in the source, but the value is a loss.
    """

    lifetime_years: int
    """Maximum battery lifetime in years."""

    lifetime_cycles: int
    """Maximum battery lifetime in full-cycle equivalents."""

    degradation_rate_pct_per_cycle: float
    """Loss of storage volume per cycle, in percent (not a fraction)."""

    capex_gbp: float
    """Cost of purchasing and installing the battery."""

    fixed_operational_costs_gbp_per_year: float
    """Annual overhead for operating the battery in electricity markets."""
