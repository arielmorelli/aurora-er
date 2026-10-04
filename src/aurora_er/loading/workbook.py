"""What a prices workbook contains, read from its headers only."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from aurora_er.loading.errors import InputFileError


@dataclass(frozen=True, slots=True, kw_only=True)
class PriceSheet:
    """A sheet that can hold one market's prices: timestamps, then a price column."""

    sheet: str
    """Sheet name."""

    price_column: str
    """Header of the second column, holding the prices."""


def price_sheets(path: Path) -> tuple[PriceSheet, ...]:
    """Every sheet in the workbook at `path` with at least a timestamp and a price column."""
    try:
        headers = pd.read_excel(path, sheet_name=None, nrows=0)
    except (OSError, ValueError) as error:
        raise InputFileError(f"could not read the prices spreadsheet: {error}") from error
    return tuple(
        PriceSheet(sheet=str(sheet), price_column=str(frame.columns[1]))
        for sheet, frame in headers.items()
        if len(frame.columns) >= 2
    )
