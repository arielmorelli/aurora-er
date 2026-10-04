from datetime import UTC, datetime, timedelta

import pytest

from aurora_er.dto import (
    BatteryDTO,
    BatterySpecDTO,
    BatteryStateDTO,
    DispatchResultDTO,
    HorizonDTO,
    MarketDTO,
    SolveOptionsDTO,
    SolveStatus,
)
from aurora_er.solver import HighsBackend, solve
from tests.solver.attachment_data import MARKET_1_FIRST_WEEK, MARKET_2_FIRST_WEEK
from tests.solver.rules import assert_follows_brief

START = datetime(2018, 1, 1, tzinfo=UTC)
ONE_WEEK = timedelta(days=7)


def _attachment_1_battery() -> BatteryDTO:
    return BatteryDTO(
        spec=BatterySpecDTO(
            max_charging_rate_mw=2,
            max_discharging_rate_mw=2,
            max_storage_volume_mwh=4,
            charging_loss_fraction=0.05,
            discharging_loss_fraction=0.05,
            lifetime_years=10,
            lifetime_cycles=5000,
            degradation_rate_pct_per_cycle=0.001,
            capex_gbp=500_000,
            fixed_operational_costs_gbp_per_year=5_000,
        ),
        state=BatteryStateDTO(stored_energy_mwh=0, cycles_used=0, commissioned_at=START),
    )


def _attachment_2_markets() -> list[MarketDTO]:
    return [
        MarketDTO(
            name="Market 1",
            horizon_start=START,
            horizon_end=START + ONE_WEEK,
            step_length=timedelta(minutes=30),
            buy_prices_gbp_per_mwh=MARKET_1_FIRST_WEEK,
            sell_prices_gbp_per_mwh=MARKET_1_FIRST_WEEK,
        ),
        MarketDTO(
            name="Market 2",
            horizon_start=START,
            horizon_end=START + ONE_WEEK,
            step_length=timedelta(hours=1),
            buy_prices_gbp_per_mwh=MARKET_2_FIRST_WEEK,
            sell_prices_gbp_per_mwh=MARKET_2_FIRST_WEEK,
        ),
    ]


def _solve_first_week(*, enforce_cycle_pace: bool) -> DispatchResultDTO:
    return solve(
        _attachment_1_battery(),
        HorizonDTO(start=START, end=START + ONE_WEEK),
        _attachment_2_markets(),
        SolveOptionsDTO(enforce_cycle_pace=enforce_cycle_pace, time_limit_seconds=60, mip_gap=0),
        HighsBackend(),
    )


@pytest.fixture(scope="module")
def first_week() -> DispatchResultDTO:
    return _solve_first_week(enforce_cycle_pace=False)


@pytest.fixture(scope="module")
def first_week_paced() -> DispatchResultDTO:
    return _solve_first_week(enforce_cycle_pace=True)


def test_solves_to_optimality(first_week: DispatchResultDTO) -> None:
    assert first_week.status is SolveStatus.OPTIMAL


def test_follows_the_brief(first_week: DispatchResultDTO) -> None:
    assert_follows_brief(first_week, _attachment_1_battery(), _attachment_2_markets())


def test_result_covers_the_week_on_each_market_step(first_week: DispatchResultDTO) -> None:
    assert [len(market.charge_mw) for market in first_week.markets] == [336, 168]
    assert len(first_week.stored_energy_mwh) == 337


def test_trades_profitably_in_both_markets(first_week: DispatchResultDTO) -> None:
    assert first_week.market_profit_gbp > 0
    assert all(sum(market.discharge_mw) > 0 for market in first_week.markets)


def test_charges_purchase_and_one_year_of_opex(first_week: DispatchResultDTO) -> None:
    assert first_week.replacements == 0
    assert first_week.capex_gbp == 500_000
    assert first_week.opex_gbp == 5_000
    assert first_week.battery_value_start_gbp == 0


def test_values_the_battery_by_cycles_left(first_week: DispatchResultDTO) -> None:
    cycles_left = 5000 - first_week.cycles_used_in_horizon
    assert first_week.battery_value_end_gbp == pytest.approx(500_000 * cycles_left / 5000)


def test_trading_earns_more_than_the_wear_it_causes(first_week: DispatchResultDTO) -> None:
    wear_gbp = first_week.capex_gbp - first_week.battery_value_end_gbp
    assert first_week.market_profit_gbp > wear_gbp


def test_final_state_carries_cycles_and_energy(first_week: DispatchResultDTO) -> None:
    assert first_week.final_state.cycles_used == pytest.approx(first_week.cycles_used_in_horizon)
    assert first_week.final_state.stored_energy_mwh == first_week.stored_energy_mwh[-1]
    assert first_week.final_state.commissioned_at == START


def test_profit_matches_recorded_optimum(
    first_week: DispatchResultDTO, first_week_paced: DispatchResultDTO
) -> None:
    assert first_week.market_profit_gbp == pytest.approx(973.8171, abs=1e-3)
    assert first_week.cycles_used_in_horizon == pytest.approx(6.5262, abs=1e-4)


def test_wear_cost_keeps_cycling_below_the_pace_cap(
    first_week: DispatchResultDTO, first_week_paced: DispatchResultDTO
) -> None:
    days_in_ten_years = 3652
    weekly_share = 5000 * 7 / days_in_ten_years
    assert first_week.cycles_used_in_horizon < weekly_share
    assert first_week_paced.market_profit_gbp == pytest.approx(first_week.market_profit_gbp)
    assert_follows_brief(first_week_paced, _attachment_1_battery(), _attachment_2_markets())
