import dataclasses
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

import pytest

from aurora_er.dto import InvalidDTOError
from aurora_er.example import example_config
from aurora_er.solver import WindowSize
from aurora_er.ui.form import (
    MarketChoice,
    RunForm,
    config_in,
    form_from_config,
    market_name,
    missing_fields,
    utc_datetime,
)

START = datetime(2018, 1, 1, tzinfo=UTC)
ALL_FILES = {"battery parameters spreadsheet": True, "market prices spreadsheet": True}


def _complete() -> RunForm:
    return RunForm(
        stored_energy_mwh=1.0,
        cycles_used=2.0,
        commissioned_at=START,
        start=START,
        end=datetime(2018, 2, 1, tzinfo=UTC),
        window_size=WindowSize.WEEK,
        enforce_cycle_pace=True,
        time_limit_seconds=60.0,
        mip_gap=0.01,
        markets=(
            MarketChoice(
                sheet="Half-hourly data",
                price_column="Market 1 Price [£/MWh]",
                step_length=timedelta(minutes=30),
            ),
            MarketChoice(sheet="Quarter-hourly", price_column="Price", step_length=None),
        ),
    )


def _with_all_steps() -> RunForm:
    form = _complete()
    return dataclasses.replace(
        form,
        markets=(
            form.markets[0],
            dataclasses.replace(form.markets[1], step_length=timedelta(minutes=15)),
        ),
    )


def test_utc_datetime_combines_date_and_time() -> None:
    assert utc_datetime(date(2018, 1, 1), time(6, 30)) == datetime(2018, 1, 1, 6, 30, tzinfo=UTC)


@pytest.mark.parametrize(("day", "clock"), [(None, time(0)), (date(2018, 1, 1), None)])
def test_utc_datetime_needs_both(day: date | None, clock: time | None) -> None:
    assert utc_datetime(day, clock) is None


def test_complete_form_has_nothing_missing() -> None:
    assert missing_fields(_with_all_steps(), ALL_FILES) == ()


def test_lists_every_missing_value_in_screen_order() -> None:
    empty = dataclasses.replace(_with_all_steps(), commissioned_at=None, end=None, window_size=None)
    files = {"battery parameters spreadsheet": False, "market prices spreadsheet": True}
    assert missing_fields(empty, files) == (
        "Upload the battery parameters spreadsheet.",
        "Set when the battery was commissioned.",
        "Set the horizon start and end.",
        "Choose a window size.",
    )


def test_config_uses_the_attachment_layout_in_the_folder() -> None:
    config = config_in(_with_all_steps(), Path("/uploads"))
    assert config.battery_sheet.path == Path("/uploads/battery.xlsx")
    assert {sheet.path for sheet in config.market_sheets} == {Path("/uploads/prices.xlsx")}
    assert config.window_size is WindowSize.WEEK
    assert config.options.mip_gap == 0.01
    assert config.battery_state.cycles_used == 2.0


def test_config_rejects_incomplete_form() -> None:
    with pytest.raises(ValueError, match="incomplete"):
        config_in(dataclasses.replace(_with_all_steps(), start=None), Path("/uploads"))


def test_config_rejects_out_of_range_values() -> None:
    with pytest.raises(InvalidDTOError, match="mip_gap"):
        config_in(dataclasses.replace(_with_all_steps(), mip_gap=1.5), Path("/uploads"))


def test_form_from_config_reproduces_the_config() -> None:
    folder = Path("/uploads")
    form = form_from_config(config_in(_with_all_steps(), folder))
    assert form == _with_all_steps()


def test_form_from_example_matches_the_example_run() -> None:
    form = form_from_config(example_config(Path("inputs")))
    assert form.window_size is WindowSize.MONTH
    assert (form.start, form.end) == (START, datetime(2021, 1, 1, tzinfo=UTC))


def test_asks_for_each_missing_step() -> None:
    assert missing_fields(_complete(), ALL_FILES) == (
        'Choose the step for sheet "Quarter-hourly".',
    )


def test_reports_prices_without_market_sheets() -> None:
    no_markets = dataclasses.replace(_with_all_steps(), markets=())
    assert missing_fields(no_markets, ALL_FILES) == (
        "The market prices spreadsheet has no sheet with timestamps and prices.",
    )


def test_config_rejects_a_market_without_step() -> None:
    with pytest.raises(ValueError, match="incomplete"):
        config_in(_complete(), Path("/uploads"))


def test_config_builds_one_market_per_sheet_with_its_step() -> None:
    sheets = config_in(_with_all_steps(), Path("/uploads")).market_sheets
    assert [(s.name, s.sheet, s.step_length) for s in sheets] == [
        ("Market 1", "Half-hourly data", timedelta(minutes=30)),
        ("Quarter-hourly", "Quarter-hourly", timedelta(minutes=15)),
    ]
    assert all(s.buy_price_column == s.sell_price_column for s in sheets)
    assert all(s.timezone == "UTC" for s in sheets)


@pytest.mark.parametrize(
    ("sheet", "column", "name"),
    [
        ("Half-hourly data", "Market 1 Price [£/MWh]", "Market 1"),
        ("Intraday", "Price", "Intraday"),
        ("Day ahead", "Spot price", "Day ahead"),
    ],
)
def test_market_name(sheet: str, column: str, name: str) -> None:
    choice = MarketChoice(sheet=sheet, price_column=column, step_length=None)
    assert market_name(choice) == name


def test_example_markets_have_their_steps() -> None:
    markets = form_from_config(example_config(Path("inputs"))).markets
    assert [market.step_length for market in markets] == [
        timedelta(minutes=30),
        timedelta(hours=1),
    ]
