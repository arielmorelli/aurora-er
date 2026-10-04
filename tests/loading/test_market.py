from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from aurora_er.loading import InputFileError, MarketSheet, market_from_frame, read_market

PRICE = "Market 1 Price [£/MWh]"
HALF_HOUR = timedelta(minutes=30)


def _sheet(*, timezone: str = "UTC", path: Path = Path("unused.xlsx")) -> MarketSheet:
    return MarketSheet(
        name="Market 1",
        path=path,
        sheet="Half-hourly data",
        buy_price_column=PRICE,
        sell_price_column=PRICE,
        timezone=timezone,
        step_length=HALF_HOUR,
    )


def _frame(timestamps: list[str], prices: list[object]) -> pd.DataFrame:
    return pd.DataFrame({"Unnamed: 0": pd.to_datetime(timestamps, format="ISO8601"), PRICE: prices})


def _first_two_hours() -> pd.DataFrame:
    return _frame(
        ["2018-01-01 00:00", "2018-01-01 00:30", "2018-01-01 01:00", "2018-01-01 01:30"],
        [48.47, 49.81, 53.65, 52.48],
    )


def test_builds_market_on_utc_grid() -> None:
    market = market_from_frame(_first_two_hours(), _sheet()).market
    assert market.name == "Market 1"
    assert market.horizon_start == datetime(2018, 1, 1, tzinfo=UTC)
    assert market.horizon_end == datetime(2018, 1, 1, 2, tzinfo=UTC)
    assert market.step_length == HALF_HOUR
    assert market.buy_prices_gbp_per_mwh == (48.47, 49.81, 53.65, 52.48)
    assert market.sell_prices_gbp_per_mwh == market.buy_prices_gbp_per_mwh


def test_reads_buy_and_sell_from_their_columns() -> None:
    frame = _first_two_hours().assign(Sell=[1.0, 2.0, 3.0, 4.0])
    sheet = MarketSheet(
        name="Market 1",
        path=Path("unused.xlsx"),
        sheet="s",
        buy_price_column=PRICE,
        sell_price_column="Sell",
        timezone="UTC",
        step_length=HALF_HOUR,
    )
    market = market_from_frame(frame, sheet).market
    assert market.sell_prices_gbp_per_mwh == (1.0, 2.0, 3.0, 4.0)


def test_converts_local_timestamps_to_utc() -> None:
    summer = _frame(["2018-07-01 01:00", "2018-07-01 01:30"], [1.0, 2.0])
    market = market_from_frame(summer, _sheet(timezone="Europe/London")).market
    assert market.horizon_start == datetime(2018, 7, 1, 0, 0, tzinfo=UTC)


def test_snaps_rounding_noise_to_the_grid() -> None:
    noisy = _frame(["2018-01-01 00:00", "2018-01-01 00:29:59.994"], [1.0, 2.0])
    assert market_from_frame(noisy, _sheet()).misplaced == ()


def test_reports_mislabelled_rows_and_keeps_their_position() -> None:
    clock_change_day = _frame(
        ["2018-03-25 00:30", "2018-03-25 02:00", "2018-03-25 02:30", "2018-03-25 02:00"],
        [61.52, 55.37, 55.37, 46.77],
    )
    loaded = market_from_frame(clock_change_day, _sheet())
    assert [entry.row for entry in loaded.misplaced] == [1, 2]
    assert loaded.misplaced[0].recorded == datetime(2018, 3, 25, 2, 0, tzinfo=UTC)
    assert loaded.misplaced[0].expected == datetime(2018, 3, 25, 1, 0, tzinfo=UTC)
    assert loaded.market.buy_prices_gbp_per_mwh == (61.52, 55.37, 55.37, 46.77)


def test_ignores_trailing_empty_rows() -> None:
    padded = pd.concat(
        [_first_two_hours(), pd.DataFrame({"Unnamed: 0": [pd.NaT], PRICE: [None]})],
        ignore_index=True,
    )
    assert market_from_frame(padded, _sheet()).market.step_count == 4


def test_rejects_missing_price_column() -> None:
    with pytest.raises(InputFileError, match="no column"):
        market_from_frame(_first_two_hours().drop(columns=[PRICE]).assign(Other=1.0), _sheet())


def test_rejects_missing_price() -> None:
    gap = _frame(["2018-01-01 00:00", "2018-01-01 00:30"], [1.0, "n/a"])
    with pytest.raises(InputFileError, match="data row 1"):
        market_from_frame(gap, _sheet())


def test_rejects_sheet_without_rows() -> None:
    with pytest.raises(InputFileError, match="no data rows"):
        market_from_frame(_frame([], []), _sheet())


def test_reads_spreadsheet_file(tmp_path: Path) -> None:
    path = tmp_path / "prices.xlsx"
    _first_two_hours().to_excel(path, sheet_name="Half-hourly data", index=False)
    loaded = read_market(_sheet(path=path))
    assert loaded.market.buy_prices_gbp_per_mwh == (48.47, 49.81, 53.65, 52.48)
