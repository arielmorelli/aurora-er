"""Read a solved model back into result DTOs."""

from datetime import datetime
from typing import Any

import pyomo.environ as pyo

from aurora_er.dto import BatteryStateDTO, DispatchResultDTO, MarketDispatchDTO
from aurora_er.solver.backend import BackendOutcome
from aurora_er.solver.problem import DispatchProblem, PreparedMarket, battery_value_gbp


def build_result(
    problem: DispatchProblem, model: Any, outcome: BackendOutcome
) -> DispatchResultDTO:
    """Assemble the result DTO from the solution loaded into `model`."""
    markets = tuple(
        _market_dispatch(model, index, market) for index, market in enumerate(problem.markets)
    )
    stored = _values(model.stored, problem.base_step_count + 1)
    cycles = _values(model.cycles, problem.base_step_count + 1)
    replaced = tuple(round(pyo.value(model.replaced[b])) for b in model.boundaries)
    calendar_replaced = _calendar_replaced(model, problem)
    replacements = replaced[-1] + int(calendar_replaced)
    market_profit = sum(market.profit_gbp for market in markets)
    capex = problem.initial_capex_gbp + replacements * problem.battery.spec.capex_gbp
    battery_value_end: float = battery_value_gbp(problem.battery.spec, cycles[-1])
    return DispatchResultDTO(
        horizon=problem.horizon,
        status=outcome.status,
        mip_gap=outcome.mip_gap,
        market_profit_gbp=market_profit,
        capex_gbp=capex,
        opex_gbp=problem.opex_gbp,
        battery_value_start_gbp=problem.battery_value_start_gbp,
        battery_value_end_gbp=battery_value_end,
        net_profit_gbp=market_profit
        - capex
        - problem.opex_gbp
        + battery_value_end
        - problem.battery_value_start_gbp,
        markets=markets,
        energy_step_length=problem.base_step,
        stored_energy_mwh=stored,
        cycles_used_in_horizon=cycles_in_horizon(problem, markets),
        replacements=replacements,
        final_state=BatteryStateDTO(
            stored_energy_mwh=stored[-1],
            cycles_used=cycles[-1],
            commissioned_at=last_commissioning(problem, replaced, calendar_replaced),
        ),
    )


def cycles_in_horizon(problem: DispatchProblem, markets: tuple[MarketDispatchDTO, ...]) -> float:
    """Full-cycle equivalents drained from storage over the horizon, across all batteries."""
    spec = problem.battery.spec
    discharged_mwh = sum(
        sum(market.discharge_mw) * prepared.interval_hours
        for market, prepared in zip(markets, problem.markets, strict=True)
    )
    drained_mwh = discharged_mwh / (1 - spec.discharging_loss_fraction)
    return drained_mwh / spec.max_storage_volume_mwh


def last_commissioning(
    problem: DispatchProblem, replaced: tuple[int, ...], calendar_replaced: bool
) -> datetime:
    """When the battery installed at the end of the horizon was commissioned."""
    events = [
        boundary
        for boundary in range(1, len(replaced))
        if replaced[boundary] > replaced[boundary - 1]
    ]
    if calendar_replaced and problem.calendar_end_boundary is not None:
        events.append(problem.calendar_end_boundary)
    if not events:
        return problem.battery.state.commissioned_at
    return problem.boundary_time(max(events))


def _calendar_replaced(model: Any, problem: DispatchProblem) -> bool:
    if problem.calendar_end_boundary is None:
        return False
    replaced_before: float = pyo.value(model.replaced_before_calendar_end)
    return round(replaced_before) == 0


def _market_dispatch(model: Any, index: int, market: PreparedMarket) -> MarketDispatchDTO:
    charge = tuple(
        max(0.0, pyo.value(model.charge[index, interval]))
        for interval in range(market.interval_count)
    )
    discharge = tuple(
        max(0.0, pyo.value(model.discharge[index, interval]))
        for interval in range(market.interval_count)
    )
    profit = market.interval_hours * sum(
        sell * out - buy * into
        for sell, out, buy, into in zip(
            market.sell_prices_gbp_per_mwh,
            discharge,
            market.buy_prices_gbp_per_mwh,
            charge,
            strict=True,
        )
    )
    return MarketDispatchDTO(
        name=market.name,
        step_length=market.step_length,
        charge_mw=charge,
        discharge_mw=discharge,
        profit_gbp=profit,
    )


def _values(variable: Any, count: int) -> tuple[float, ...]:
    return tuple(max(0.0, pyo.value(variable[index])) for index in range(count))
