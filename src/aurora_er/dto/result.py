"""Outcome of a battery dispatch solve."""

import math
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from aurora_er.dto.battery import BatteryStateDTO
from aurora_er.dto.horizon import HorizonDTO
from aurora_er.dto.validation import are_finite, require


class SolveStatus(StrEnum):
    """How good the returned dispatch is."""

    OPTIMAL = "optimal"
    """Proven optimal within the requested MIP gap."""

    FEASIBLE = "feasible"
    """Valid but not proven optimal, e.g. the time limit was reached."""


@dataclass(frozen=True, slots=True, kw_only=True)
class MarketDispatchDTO:
    """Power committed to one market, on that market's own steps."""

    name: str
    """Market identifier, as in the input ``MarketDTO``."""

    step_length: timedelta
    """Duration of each value below."""

    charge_mw: tuple[float, ...]
    """Power imported from this market per step (grid side)."""

    discharge_mw: tuple[float, ...]
    """Power exported to this market per step (grid side)."""

    profit_gbp: float
    """Sales minus purchases in this market over the horizon."""

    def __post_init__(self) -> None:
        require(bool(self.name.strip()), "name must not be blank")
        require(self.step_length > timedelta(0), "step_length must be positive")
        require(
            len(self.charge_mw) == len(self.discharge_mw),
            "charge_mw and discharge_mw must have the same length",
        )
        require(
            are_finite((*self.charge_mw, *self.discharge_mw, self.profit_gbp)),
            "power and profit must be finite",
        )
        require(
            all(power >= 0 for power in (*self.charge_mw, *self.discharge_mw)),
            "charge_mw and discharge_mw must not be negative",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class DispatchResultDTO:
    """Optimal (or best found) dispatch of the battery over a horizon."""

    horizon: HorizonDTO
    """Window that was optimised."""

    status: SolveStatus
    """Whether the dispatch is proven optimal."""

    mip_gap: float
    """Relative gap between the dispatch found and the best possible bound."""

    market_profit_gbp: float
    """Sales minus purchases across all markets."""

    capex_gbp: float
    """Initial purchase (if in the horizon) plus replacements."""

    opex_gbp: float
    """Fixed operational costs for operating years started in the horizon."""

    battery_value_start_gbp: float
    """Value of the battery owned before the horizon; 0 if bought at its start."""

    battery_value_end_gbp: float
    """Value of the installed battery at the end, from the cycles it has left."""

    net_profit_gbp: float
    """Market profit minus capex and opex, plus the change in battery value."""

    markets: tuple[MarketDispatchDTO, ...]
    """Dispatch per market, in the order of the input markets."""

    energy_step_length: timedelta
    """Spacing of ``stored_energy_mwh``: the finest market step."""

    stored_energy_mwh: tuple[float, ...]
    """Energy in storage at every step boundary, from horizon start to end."""

    cycles_used_in_horizon: float
    """Full-cycle equivalents used across all batteries during the horizon."""

    replacements: int
    """Batteries replaced in the horizon, for cycles or calendar age."""

    final_state: BatteryStateDTO
    """Battery state at the end of the horizon."""

    def __post_init__(self) -> None:
        require(self.mip_gap >= 0, "mip_gap must not be negative")
        require(
            are_finite(
                (
                    self.market_profit_gbp,
                    self.capex_gbp,
                    self.opex_gbp,
                    self.battery_value_start_gbp,
                    self.battery_value_end_gbp,
                    self.net_profit_gbp,
                    self.cycles_used_in_horizon,
                    *self.stored_energy_mwh,
                )
            ),
            "money, cycles and stored energy must be finite",
        )
        require(self.capex_gbp >= 0, "capex_gbp must not be negative")
        require(self.opex_gbp >= 0, "opex_gbp must not be negative")
        require(self.battery_value_start_gbp >= 0, "battery_value_start_gbp must not be negative")
        require(self.battery_value_end_gbp >= 0, "battery_value_end_gbp must not be negative")
        expected_net = (
            self.market_profit_gbp
            - self.capex_gbp
            - self.opex_gbp
            + self.battery_value_end_gbp
            - self.battery_value_start_gbp
        )
        require(
            math.isclose(self.net_profit_gbp, expected_net, abs_tol=1e-9),
            "net_profit_gbp must equal market profit - capex - opex + battery value change",
        )
        require(bool(self.markets), "markets must not be empty")
        require(self.energy_step_length > timedelta(0), "energy_step_length must be positive")
        require(len(self.stored_energy_mwh) >= 2, "stored_energy_mwh must cover the horizon")
        require(
            all(energy >= 0 for energy in self.stored_energy_mwh),
            "stored_energy_mwh must not be negative",
        )
        require(self.cycles_used_in_horizon >= 0, "cycles_used_in_horizon must not be negative")
        require(self.replacements >= 0, "replacements must not be negative")
