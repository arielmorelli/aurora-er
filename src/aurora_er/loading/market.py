"""Market prices from a sheet laid out like `inputs/Attachment 2.xlsx`.

The sheet has timestamps in the first column and prices in named columns.
Rows are trusted to be consecutive market intervals: the time grid is built
from the first timestamp and the step length, and every recorded timestamp is
checked against its slot. Timestamps off their slot are reported, not fixed
silently.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from aurora_er.dto import MarketDTO
from aurora_er.loading.errors import InputFileError


@dataclass(frozen=True, slots=True, kw_only=True)
class MarketSheet:
    """Where one market's prices are and how to read them."""

    name: str
    """Market identifier given to the resulting `MarketDTO`."""

    path: Path
    """Spreadsheet file."""

    sheet: str
    """Sheet name inside the file."""

    buy_price_column: str
    """Column with the price paid when charging."""

    sell_price_column: str
    """Column with the price received when discharging."""

    timezone: str
    """IANA zone the recorded timestamps are in, e.g. `UTC`."""

    step_length: timedelta
    """Duration of one market interval (one row)."""


@dataclass(frozen=True, slots=True, kw_only=True)
class MisplacedTimestamp:
    """A row whose recorded timestamp does not match its position on the grid."""

    row: int
    """Zero-based data row."""

    recorded: datetime
    """Timestamp found in the file, in the sheet's timezone."""

    expected: datetime
    """Timestamp of the row's slot on the grid, in UTC."""


@dataclass(frozen=True, slots=True, kw_only=True)
class LoadedMarket:
    """A market read from file, with any timestamps that did not fit the grid."""

    market: MarketDTO
    """Prices on a regular UTC grid."""

    misplaced: tuple[MisplacedTimestamp, ...]
    """Rows whose recorded timestamp differs from their slot."""


def read_market(source: MarketSheet) -> LoadedMarket:
    """Read and convert one market's price sheet."""
    frame = pd.read_excel(source.path, sheet_name=source.sheet)
    return market_from_frame(frame, source)


def market_from_frame(frame: pd.DataFrame, source: MarketSheet) -> LoadedMarket:
    """Convert a timestamp/price table to a `MarketDTO` on a regular UTC grid."""
    for column in (source.buy_price_column, source.sell_price_column):
        if column not in frame.columns:
            raise InputFileError(f"{source.name}: no column {column!r}")
    rows = frame.dropna(how="all").reset_index(drop=True)
    if rows.empty:
        raise InputFileError(f"{source.name}: no data rows")
    recorded = pd.to_datetime(rows.iloc[:, 0]).dt.round(source.step_length)
    localized = recorded.dt.tz_localize(source.timezone).dt.tz_convert("UTC")
    start = localized.iloc[0].to_pydatetime()
    expected = pd.Series([start + index * source.step_length for index in range(len(rows))])
    misplaced = tuple(
        MisplacedTimestamp(
            row=index,
            recorded=localized.iloc[index].to_pydatetime(),
            expected=expected.iloc[index],
        )
        for index in range(len(rows))
        if localized.iloc[index] != expected.iloc[index]
    )
    return LoadedMarket(
        market=MarketDTO(
            name=source.name,
            horizon_start=start,
            horizon_end=start + len(rows) * source.step_length,
            step_length=source.step_length,
            buy_prices_gbp_per_mwh=_prices(rows, source.buy_price_column, source.name),
            sell_prices_gbp_per_mwh=_prices(rows, source.sell_price_column, source.name),
        ),
        misplaced=misplaced,
    )


def _prices(rows: pd.DataFrame, column: str, market: str) -> tuple[float, ...]:
    prices = pd.to_numeric(rows[column], errors="coerce")
    if prices.isna().any():
        first_bad = int(prices.isna().to_numpy().argmax())
        raise InputFileError(f"{market}: {column!r} has no number in data row {first_bad}")
    return tuple(float(price) for price in prices)
