"""`RunConfig` to and from the session's `config.yaml`.

Spreadsheet paths are stored relative to the session folder, so a session
folder can be copied (for a rerun) without editing its config.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from aurora_er.config import RunConfig
from aurora_er.dto import BatteryStateDTO, HorizonDTO, SolveOptionsDTO
from aurora_er.loading import BatterySheet, MarketSheet
from aurora_er.solver import WindowSize


def config_to_yaml(config: RunConfig, session_dir: Path) -> str:
    """Serialise `config`, writing spreadsheet paths relative to `session_dir`."""
    document = {
        "battery": {
            "file": config.battery_sheet.path.relative_to(session_dir).as_posix(),
            "sheet": config.battery_sheet.sheet,
            "state": {
                "stored_energy_mwh": config.battery_state.stored_energy_mwh,
                "cycles_used": config.battery_state.cycles_used,
                "commissioned_at": config.battery_state.commissioned_at.isoformat(),
            },
        },
        "markets": [
            {
                "name": sheet.name,
                "file": sheet.path.relative_to(session_dir).as_posix(),
                "sheet": sheet.sheet,
                "buy_price_column": sheet.buy_price_column,
                "sell_price_column": sheet.sell_price_column,
                "timezone": sheet.timezone,
                "step_minutes": sheet.step_length / timedelta(minutes=1),
            }
            for sheet in config.market_sheets
        ],
        "horizon": {
            "start": config.horizon.start.isoformat(),
            "end": config.horizon.end.isoformat(),
            "window_size": config.window_size.value,
        },
        "solver": {
            "enforce_cycle_pace": config.options.enforce_cycle_pace,
            "time_limit_seconds": config.options.time_limit_seconds,
            "mip_gap": config.options.mip_gap,
        },
    }
    return yaml.safe_dump(document, sort_keys=False, allow_unicode=True)


def config_from_yaml(text: str, session_dir: Path) -> RunConfig:
    """Parse a `config.yaml`, resolving spreadsheet paths against `session_dir`."""
    document: dict[str, Any] = yaml.safe_load(text)
    battery = document["battery"]
    state = battery["state"]
    horizon = document["horizon"]
    solver = document["solver"]
    return RunConfig(
        battery_sheet=BatterySheet(path=session_dir / battery["file"], sheet=battery["sheet"]),
        battery_state=BatteryStateDTO(
            stored_energy_mwh=float(state["stored_energy_mwh"]),
            cycles_used=float(state["cycles_used"]),
            commissioned_at=_datetime(state["commissioned_at"]),
        ),
        market_sheets=tuple(
            MarketSheet(
                name=market["name"],
                path=session_dir / market["file"],
                sheet=market["sheet"],
                buy_price_column=market["buy_price_column"],
                sell_price_column=market["sell_price_column"],
                timezone=market["timezone"],
                step_length=timedelta(minutes=float(market["step_minutes"])),
            )
            for market in document["markets"]
        ),
        horizon=HorizonDTO(start=_datetime(horizon["start"]), end=_datetime(horizon["end"])),
        window_size=WindowSize(horizon["window_size"]),
        options=SolveOptionsDTO(
            enforce_cycle_pace=bool(solver["enforce_cycle_pace"]),
            time_limit_seconds=float(solver["time_limit_seconds"]),
            mip_gap=float(solver["mip_gap"]),
        ),
    )


def _datetime(value: str | datetime) -> datetime:
    return value if isinstance(value, datetime) else datetime.fromisoformat(value)
