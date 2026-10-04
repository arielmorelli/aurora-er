"""Layout of the provided spreadsheets (`inputs/Attachment 1.xlsx` and `Attachment 2.xlsx`).

Spreadsheets in this layout can be read without extra settings, and the
download templates are generated from it so they always match the loaders.
Both price sheets are a regular UTC grid: every day has exactly 48
half-hourly and 24 hourly rows, including clock-change days.
"""

from dataclasses import dataclass
from datetime import timedelta
from io import BytesIO
from pathlib import Path

import pandas as pd

from aurora_er.loading import BatterySheet, MarketSheet
from aurora_er.loading.battery import FIELDS_BY_LABEL, UNIT_COLUMN, VALUE_COLUMN

BATTERY_SHEET = "Data"
PRICES_TIMEZONE = "UTC"
TIMESTAMP_COLUMN = "Timestamp (UTC)"


@dataclass(frozen=True, slots=True, kw_only=True)
class MarketLayout:
    """Where one market lives in the prices spreadsheet."""

    name: str
    """Market identifier."""

    sheet: str
    """Sheet holding the market's prices."""

    price_column: str
    """Column used for both buying and selling."""

    step_length: timedelta
    """Duration of one row."""


MARKETS = (
    MarketLayout(
        name="Market 1",
        sheet="Half-hourly data",
        price_column="Market 1 Price [£/MWh]",
        step_length=timedelta(minutes=30),
    ),
    MarketLayout(
        name="Market 2",
        sheet="Hourly data",
        price_column="Market 2 Price [£/MWh]",
        step_length=timedelta(hours=1),
    ),
)


def battery_sheet(path: Path) -> BatterySheet:
    """Where the battery parameters are in a spreadsheet with the Attachment 1 layout."""
    return BatterySheet(path=path, sheet=BATTERY_SHEET)


def market_sheets(path: Path) -> tuple[MarketSheet, ...]:
    """Where each market is in a spreadsheet with the Attachment 2 layout."""
    return tuple(
        MarketSheet(
            name=market.name,
            path=path,
            sheet=market.sheet,
            buy_price_column=market.price_column,
            sell_price_column=market.price_column,
            timezone=PRICES_TIMEZONE,
            step_length=market.step_length,
        )
        for market in MARKETS
    )


def battery_template() -> bytes:
    """Empty battery parameters workbook: labels and units filled, values to complete."""
    rows = [
        {"Parameter": label, VALUE_COLUMN: None, UNIT_COLUMN: unit}
        for label, (_, unit) in FIELDS_BY_LABEL.items()
    ]
    return _workbook({BATTERY_SHEET: pd.DataFrame(rows)})


def prices_template() -> bytes:
    """Empty prices workbook: one sheet per market with timestamp and price headers."""
    return _workbook(
        {
            market.sheet: pd.DataFrame(columns=[TIMESTAMP_COLUMN, market.price_column])
            for market in MARKETS
        }
    )


def _workbook(sheets: dict[str, pd.DataFrame]) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer) as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False)
    return buffer.getvalue()
