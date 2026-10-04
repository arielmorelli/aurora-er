"""A finished session's result to and from `result.json`."""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from aurora_er.dto import (
    BatteryStateDTO,
    DispatchResultDTO,
    HorizonDTO,
    MarketDispatchDTO,
    RollingDispatchResultDTO,
    SolveStatus,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionResult:
    """What a finished session produced."""

    result: RollingDispatchResultDTO
    """Dispatch per window and totals."""

    warnings: tuple[str, ...]
    """Input warnings shown with the result, e.g. misplaced timestamps."""


def result_to_json(session_result: SessionResult) -> str:
    """Serialise a session result; datetimes as ISO 8601, durations in seconds."""
    rolling = session_result.result
    return json.dumps(
        {
            "horizon": _horizon(rolling.horizon),
            "windows": [_window(window) for window in rolling.windows],
            "warnings": list(session_result.warnings),
        }
    )


def result_from_json(text: str) -> SessionResult:
    """Parse a `result.json` back into DTOs."""
    document: dict[str, Any] = json.loads(text)
    return SessionResult(
        result=RollingDispatchResultDTO(
            horizon=_parse_horizon(document["horizon"]),
            windows=tuple(_parse_window(window) for window in document["windows"]),
        ),
        warnings=tuple(document["warnings"]),
    )


def _horizon(horizon: HorizonDTO) -> dict[str, str]:
    return {"start": horizon.start.isoformat(), "end": horizon.end.isoformat()}


def _parse_horizon(document: dict[str, str]) -> HorizonDTO:
    return HorizonDTO(
        start=datetime.fromisoformat(document["start"]),
        end=datetime.fromisoformat(document["end"]),
    )


def _window(window: DispatchResultDTO) -> dict[str, Any]:
    return {
        "horizon": _horizon(window.horizon),
        "status": window.status.value,
        "mip_gap": window.mip_gap,
        "market_profit_gbp": window.market_profit_gbp,
        "capex_gbp": window.capex_gbp,
        "opex_gbp": window.opex_gbp,
        "battery_value_start_gbp": window.battery_value_start_gbp,
        "battery_value_end_gbp": window.battery_value_end_gbp,
        "net_profit_gbp": window.net_profit_gbp,
        "markets": [
            {
                "name": market.name,
                "step_seconds": market.step_length.total_seconds(),
                "charge_mw": list(market.charge_mw),
                "discharge_mw": list(market.discharge_mw),
                "profit_gbp": market.profit_gbp,
            }
            for market in window.markets
        ],
        "energy_step_seconds": window.energy_step_length.total_seconds(),
        "stored_energy_mwh": list(window.stored_energy_mwh),
        "cycles_used_in_horizon": window.cycles_used_in_horizon,
        "replacements": window.replacements,
        "final_state": {
            "stored_energy_mwh": window.final_state.stored_energy_mwh,
            "cycles_used": window.final_state.cycles_used,
            "commissioned_at": window.final_state.commissioned_at.isoformat(),
        },
    }


def _parse_window(document: dict[str, Any]) -> DispatchResultDTO:
    final_state = document["final_state"]
    return DispatchResultDTO(
        horizon=_parse_horizon(document["horizon"]),
        status=SolveStatus(document["status"]),
        mip_gap=document["mip_gap"],
        market_profit_gbp=document["market_profit_gbp"],
        capex_gbp=document["capex_gbp"],
        opex_gbp=document["opex_gbp"],
        battery_value_start_gbp=document["battery_value_start_gbp"],
        battery_value_end_gbp=document["battery_value_end_gbp"],
        net_profit_gbp=document["net_profit_gbp"],
        markets=tuple(
            MarketDispatchDTO(
                name=market["name"],
                step_length=timedelta(seconds=market["step_seconds"]),
                charge_mw=tuple(market["charge_mw"]),
                discharge_mw=tuple(market["discharge_mw"]),
                profit_gbp=market["profit_gbp"],
            )
            for market in document["markets"]
        ),
        energy_step_length=timedelta(seconds=document["energy_step_seconds"]),
        stored_energy_mwh=tuple(document["stored_energy_mwh"]),
        cycles_used_in_horizon=document["cycles_used_in_horizon"],
        replacements=document["replacements"],
        final_state=BatteryStateDTO(
            stored_energy_mwh=final_state["stored_energy_mwh"],
            cycles_used=final_state["cycles_used"],
            commissioned_at=datetime.fromisoformat(final_state["commissioned_at"]),
        ),
    )
