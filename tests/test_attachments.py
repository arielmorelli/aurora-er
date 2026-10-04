from datetime import timedelta
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from aurora_er.attachments import (
    MARKETS,
    battery_sheet,
    battery_template,
    market_sheets,
    prices_template,
)
from aurora_er.loading import (
    InputFileError,
    battery_spec_from_frame,
    read_battery_spec,
    read_market,
)

INPUTS = Path(__file__).parents[1] / "inputs"


def test_battery_sheet_points_at_data_sheet() -> None:
    sheet = battery_sheet(Path("b.xlsx"))
    assert (sheet.path, sheet.sheet) == (Path("b.xlsx"), "Data")


def test_market_sheets_follow_attachment_2() -> None:
    sheets = market_sheets(Path("p.xlsx"))
    assert [(s.name, s.sheet, s.step_length) for s in sheets] == [
        ("Market 1", "Half-hourly data", timedelta(minutes=30)),
        ("Market 2", "Hourly data", timedelta(hours=1)),
    ]
    assert all(s.buy_price_column == s.sell_price_column for s in sheets)
    assert all(s.timezone == "UTC" for s in sheets)


def test_layout_reads_the_provided_attachments() -> None:
    assert read_battery_spec(battery_sheet(INPUTS / "Attachment 1.xlsx")).capex_gbp == 500_000
    first = read_market(market_sheets(INPUTS / "Attachment 2.xlsx")[1])
    assert first.market.step_count == 26_304


def test_battery_template_has_every_parameter_and_no_values() -> None:
    frame = pd.read_excel(BytesIO(battery_template()), sheet_name="Data")
    assert len(frame) == 10
    assert frame["Values"].isna().all()
    with pytest.raises(InputFileError, match="'Max charging rate' has no value"):
        battery_spec_from_frame(frame)


def test_battery_template_becomes_valid_once_filled() -> None:
    frame = pd.read_excel(BytesIO(battery_template()), sheet_name="Data")
    frame["Values"] = [2, 2, 4, 0.05, 0.05, 10, 5000, 0.001, 500000, 5000]
    assert battery_spec_from_frame(frame).lifetime_cycles == 5000


def test_prices_template_has_one_sheet_per_market_with_headers() -> None:
    sheets = pd.read_excel(BytesIO(prices_template()), sheet_name=None)
    assert list(sheets) == [market.sheet for market in MARKETS]
    for market in MARKETS:
        assert list(sheets[market.sheet].columns)[1] == market.price_column
        assert sheets[market.sheet].empty
