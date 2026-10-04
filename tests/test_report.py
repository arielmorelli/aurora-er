from datetime import UTC, datetime, timedelta

from aurora_er.dto import (
    BatteryStateDTO,
    DispatchResultDTO,
    HorizonDTO,
    MarketDispatchDTO,
    MarketDTO,
    RollingDispatchResultDTO,
    SolveStatus,
)
from aurora_er.loading import LoadedMarket, MisplacedTimestamp
from aurora_er.report import format_summary, format_window

START = datetime(2018, 1, 1, tzinfo=UTC)


def _result() -> DispatchResultDTO:
    return DispatchResultDTO(
        horizon=HorizonDTO(start=START, end=START + timedelta(hours=2)),
        status=SolveStatus.OPTIMAL,
        mip_gap=0.0,
        market_profit_gbp=1234.5,
        capex_gbp=500_000.0,
        opex_gbp=5_000.0,
        battery_value_start_gbp=0.0,
        battery_value_end_gbp=499_900.0,
        net_profit_gbp=1234.5 - 500_000 - 5_000 + 499_900,
        markets=(
            MarketDispatchDTO(
                name="Market 1",
                step_length=timedelta(minutes=30),
                charge_mw=(2.0, 2.0, 0.0, 0.0),
                discharge_mw=(0.0, 0.0, 2.0, 0.0),
                profit_gbp=1234.5,
            ),
        ),
        energy_step_length=timedelta(minutes=30),
        stored_energy_mwh=(0.0, 0.95, 1.9, 0.85, 0.85),
        cycles_used_in_horizon=0.26,
        replacements=0,
        final_state=BatteryStateDTO(
            stored_energy_mwh=0.85, cycles_used=0.26, commissioned_at=START
        ),
    )


def _rolling() -> RollingDispatchResultDTO:
    return RollingDispatchResultDTO(horizon=_result().horizon, windows=(_result(),))


def _loaded(misplaced: tuple[MisplacedTimestamp, ...] = ()) -> LoadedMarket:
    prices = (1.0, 2.0, 3.0, 4.0)
    return LoadedMarket(
        market=MarketDTO(
            name="Market 1",
            horizon_start=START,
            horizon_end=START + timedelta(hours=2),
            step_length=timedelta(minutes=30),
            buy_prices_gbp_per_mwh=prices,
            sell_prices_gbp_per_mwh=prices,
        ),
        misplaced=misplaced,
    )


def test_shows_status_and_money() -> None:
    summary = format_summary(_rolling(), [_loaded()])
    assert "every window optimal" in summary
    assert "Market profit         £      1,234.50" in summary
    assert "Battery value end    +£    499,900.00" in summary
    assert "Net profit            £     -3,865.50" in summary


def test_converts_power_to_energy_per_market() -> None:
    market_line = next(
        line
        for line in format_summary(_rolling(), [_loaded()]).splitlines()
        if line.startswith("Market 1 ")
    )
    assert market_line.split()[2:4] == ["2.00", "1.00"]


def test_shows_cycles_and_final_state() -> None:
    summary = format_summary(_rolling(), [_loaded()])
    assert "Cycles used: 0.26  Replacements: 0" in summary
    assert "0.85 MWh stored" in summary


def test_warns_about_misplaced_timestamps() -> None:
    misplaced = MisplacedTimestamp(
        row=3986,
        recorded=datetime(2018, 3, 25, 2, tzinfo=UTC),
        expected=datetime(2018, 3, 25, 1, tzinfo=UTC),
    )
    summary = format_summary(_rolling(), [_loaded((misplaced,))])
    assert "Warning: Market 1 has 1 rows" in summary
    assert "row 3986: recorded 2018-03-25T02:00:00+00:00, slot 2018-03-25T01:00:00+00:00" in summary


def test_no_warning_when_all_timestamps_fit() -> None:
    assert "Warning" not in format_summary(_rolling(), [_loaded()])


def test_reports_window_count_and_optimality() -> None:
    assert "1 windows, every window optimal" in format_summary(_rolling(), [_loaded()])


def test_format_window_shows_period_status_profit_and_cycles() -> None:
    line = format_window(_result())
    assert line.startswith("2018-01-01 -> 2018-01-01  optimal")
    assert "market £  1,234.50" in line
    assert "cycles   0.26" in line
