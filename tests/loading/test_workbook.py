from pathlib import Path

import pandas as pd
import pytest

from aurora_er.loading import InputFileError, PriceSheet, price_sheets

INPUTS = Path(__file__).parents[2] / "inputs"


def test_lists_the_sheets_of_the_provided_prices() -> None:
    assert price_sheets(INPUTS / "Attachment 2.xlsx") == (
        PriceSheet(sheet="Half-hourly data", price_column="Market 1 Price [£/MWh]"),
        PriceSheet(sheet="Hourly data", price_column="Market 2 Price [£/MWh]"),
    )


def test_skips_sheets_without_a_price_column(tmp_path: Path) -> None:
    path = tmp_path / "prices.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"Time": [], "Price": []}).to_excel(writer, sheet_name="Market A", index=False)
        pd.DataFrame({"Notes": []}).to_excel(writer, sheet_name="Readme", index=False)
    assert price_sheets(path) == (PriceSheet(sheet="Market A", price_column="Price"),)


def test_rejects_a_file_that_is_not_a_workbook(tmp_path: Path) -> None:
    path = tmp_path / "prices.xlsx"
    path.write_text("not a spreadsheet", encoding="utf-8")
    with pytest.raises(InputFileError, match="could not read the prices spreadsheet"):
        price_sheets(path)
