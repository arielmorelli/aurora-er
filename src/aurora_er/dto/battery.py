"""Battery parameters (``docs/input/Attachment 1.xlsx``) and operating state."""

from dataclasses import dataclass
from datetime import datetime

from aurora_er.dto.validation import are_finite, is_timezone_aware, require


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

    def __post_init__(self) -> None:
        require(self.max_charging_rate_mw > 0, "max_charging_rate_mw must be positive")
        require(self.max_discharging_rate_mw > 0, "max_discharging_rate_mw must be positive")
        require(self.max_storage_volume_mwh > 0, "max_storage_volume_mwh must be positive")
        require(0 <= self.charging_loss_fraction < 1, "charging_loss_fraction must be in [0, 1)")
        require(
            0 <= self.discharging_loss_fraction < 1, "discharging_loss_fraction must be in [0, 1)"
        )
        require(self.lifetime_years > 0, "lifetime_years must be positive")
        require(self.lifetime_cycles > 0, "lifetime_cycles must be positive")
        require(
            self.degradation_rate_pct_per_cycle >= 0,
            "degradation_rate_pct_per_cycle must not be negative",
        )
        require(
            self.degradation_rate_pct_per_cycle * self.lifetime_cycles < 100,
            "degradation over lifetime_cycles must leave some usable volume",
        )
        require(self.capex_gbp >= 0, "capex_gbp must not be negative")
        require(
            self.fixed_operational_costs_gbp_per_year >= 0,
            "fixed_operational_costs_gbp_per_year must not be negative",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class BatteryStateDTO:
    """Condition of the installed battery at a given instant."""

    stored_energy_mwh: float
    """Energy currently held in storage."""

    cycles_used: float
    """Full-cycle equivalents used by the installed battery since it was commissioned."""

    commissioned_at: datetime
    """When the installed battery was put into service. Timezone-aware."""

    def __post_init__(self) -> None:
        require(
            are_finite((self.stored_energy_mwh, self.cycles_used)),
            "stored_energy_mwh and cycles_used must be finite",
        )
        require(self.stored_energy_mwh >= 0, "stored_energy_mwh must not be negative")
        require(self.cycles_used >= 0, "cycles_used must not be negative")
        require(is_timezone_aware(self.commissioned_at), "commissioned_at must be timezone-aware")


@dataclass(frozen=True, slots=True, kw_only=True)
class BatteryDTO:
    """A battery: its static specification and its current state."""

    spec: BatterySpecDTO
    """Technical and financial parameters."""

    state: BatteryStateDTO
    """Condition at the start of the dispatch horizon."""

    @property
    def usable_volume_mwh(self) -> float:
        """Storage volume left after degradation from the cycles already used."""
        degradation_fraction = self.spec.degradation_rate_pct_per_cycle / 100
        return self.spec.max_storage_volume_mwh * (
            1 - degradation_fraction * self.state.cycles_used
        )

    def __post_init__(self) -> None:
        require(
            self.state.cycles_used <= self.spec.lifetime_cycles,
            "state.cycles_used must not exceed spec.lifetime_cycles",
        )
        require(
            self.state.stored_energy_mwh <= self.usable_volume_mwh,
            "state.stored_energy_mwh must fit in the usable volume",
        )
