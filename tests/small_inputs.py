"""Writes a tiny but complete set of input files and the run config pointing at them."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

from aurora_er.config import RunConfig
from aurora_er.dto import BatteryStateDTO, HorizonDTO, SolveOptionsDTO
from aurora_er.loading import BatterySheet, MarketSheet
from aurora_er.solver import WindowSize
from tests.loading.test_battery import ATTACHMENT_1_ROWS

START = datetime(2018, 1, 1, tzinfo=UTC)


def write_small_inputs(folder: Path) -> RunConfig:
    """Attachment 1 battery and two hours of prices with one profitable spread."""
    write_small_spreadsheets(folder)
    return small_config(folder)


def write_small_spreadsheets(folder: Path) -> None:
    """Writes `battery.xlsx` and `prices.xlsx` into `folder`."""
    pd.DataFrame(ATTACHMENT_1_ROWS, columns=["Parameter", "Values", "Units"]).to_excel(
        folder / "battery.xlsx", sheet_name="Data", index=False
    )
    half_hourly = pd.DataFrame(
        {
            "Time": pd.date_range("2018-01-01", periods=4, freq="30min"),
            "Price": [10.0, 10.0, 300.0, 300.0],
        }
    )
    hourly = pd.DataFrame(
        {"Time": pd.date_range("2018-01-01", periods=2, freq="60min"), "Price": [50.0, 50.0]}
    )
    with pd.ExcelWriter(folder / "prices.xlsx") as writer:
        half_hourly.to_excel(writer, sheet_name="Half-hourly data", index=False)
        hourly.to_excel(writer, sheet_name="Hourly data", index=False)


def small_config(folder: Path) -> RunConfig:
    """Run config for the spreadsheets written by `write_small_spreadsheets` in `folder`."""
    return RunConfig(
        battery_sheet=BatterySheet(path=folder / "battery.xlsx", sheet="Data"),
        battery_state=BatteryStateDTO(
            stored_energy_mwh=0.0, cycles_used=0.0, commissioned_at=datetime(2017, 6, 1, tzinfo=UTC)
        ),
        market_sheets=(
            _prices(folder, "Market 1", "Half-hourly data", timedelta(minutes=30)),
            _prices(folder, "Market 2", "Hourly data", timedelta(hours=1)),
        ),
        horizon=HorizonDTO(start=START, end=START + timedelta(hours=2)),
        window_size=WindowSize.MONTH,
        options=SolveOptionsDTO(enforce_cycle_pace=False, time_limit_seconds=30, mip_gap=0.0),
    )


def _prices(folder: Path, name: str, sheet: str, step_length: timedelta) -> MarketSheet:
    return MarketSheet(
        name=name,
        path=folder / "prices.xlsx",
        sheet=sheet,
        buy_price_column="Price",
        sell_price_column="Price",
        timezone="UTC",
        step_length=step_length,
    )
