"""Pyomo MILP for battery dispatch, as specified in `docs/problem-definition.md`."""

from typing import Any

import pyomo.environ as pyo

from aurora_er.solver.problem import DispatchProblem, battery_value_gbp


def build_model(problem: DispatchProblem) -> Any:
    """Build the dispatch MILP for `problem`; variables are left unsolved."""
    model = pyo.ConcreteModel(name="battery_dispatch")
    _add_sets(model, problem)
    _add_variables(model, problem)
    _add_power_constraints(model, problem)
    _add_energy_constraints(model, problem)
    _add_lifetime_constraints(model, problem)
    _add_objective(model, problem)
    return model


def total_charge_mw(model: Any, problem: DispatchProblem, step: int) -> Any:
    """Charging power across all markets during base `step`."""
    return sum(
        model.charge[index, market.interval_of(step)]
        for index, market in enumerate(problem.markets)
    )


def total_discharge_mw(model: Any, problem: DispatchProblem, step: int) -> Any:
    """Discharging power across all markets during base `step`."""
    return sum(
        model.discharge[index, market.interval_of(step)]
        for index, market in enumerate(problem.markets)
    )


def drained_cycles(model: Any, problem: DispatchProblem, step: int) -> Any:
    """Full-cycle equivalents leaving storage during base `step`."""
    spec = problem.battery.spec
    drained_mwh = (
        problem.base_step_hours
        * total_discharge_mw(model, problem, step)
        / (1 - spec.discharging_loss_fraction)
    )
    return drained_mwh / spec.max_storage_volume_mwh


def _add_sets(model: Any, problem: DispatchProblem) -> None:
    model.steps = pyo.RangeSet(0, problem.base_step_count - 1)
    model.boundaries = pyo.RangeSet(0, problem.base_step_count)
    model.intervals = pyo.Set(
        dimen=2,
        initialize=[
            (index, interval)
            for index, market in enumerate(problem.markets)
            for interval in range(market.interval_count)
        ],
    )


def _add_variables(model: Any, problem: DispatchProblem) -> None:
    spec = problem.battery.spec
    model.charge = pyo.Var(model.intervals, bounds=(0, spec.max_charging_rate_mw))
    model.discharge = pyo.Var(model.intervals, bounds=(0, spec.max_discharging_rate_mw))
    model.charging = pyo.Var(model.steps, within=pyo.Binary)
    model.stored = pyo.Var(model.boundaries, within=pyo.NonNegativeReals)
    model.cycles = pyo.Var(model.boundaries, bounds=(0, spec.lifetime_cycles))
    model.replaced = pyo.Var(
        model.boundaries, within=pyo.NonNegativeIntegers, bounds=(0, problem.replacement_bound)
    )
    if problem.calendar_end_boundary is not None:
        model.replaced_before_calendar_end = pyo.Var(within=pyo.Binary)
        model.discarded_cycles = pyo.Var(bounds=(0, spec.lifetime_cycles))


def _add_power_constraints(model: Any, problem: DispatchProblem) -> None:
    spec = problem.battery.spec

    def charge_limit(model: Any, step: int) -> Any:
        return (
            total_charge_mw(model, problem, step)
            <= spec.max_charging_rate_mw * model.charging[step]
        )

    def discharge_limit(model: Any, step: int) -> Any:
        return total_discharge_mw(model, problem, step) <= spec.max_discharging_rate_mw * (
            1 - model.charging[step]
        )

    model.charge_limit = pyo.Constraint(model.steps, rule=charge_limit)
    model.discharge_limit = pyo.Constraint(model.steps, rule=discharge_limit)


def _add_energy_constraints(model: Any, problem: DispatchProblem) -> None:
    spec = problem.battery.spec
    degradation_fraction = spec.degradation_rate_pct_per_cycle / 100

    def energy_balance(model: Any, step: int) -> Any:
        charged = (
            problem.base_step_hours
            * (1 - spec.charging_loss_fraction)
            * total_charge_mw(model, problem, step)
        )
        drained = drained_cycles(model, problem, step) * spec.max_storage_volume_mwh
        return model.stored[step + 1] == model.stored[step] + charged - drained

    def usable_volume(model: Any, boundary: int) -> Any:
        return model.stored[boundary] <= spec.max_storage_volume_mwh * (
            1 - degradation_fraction * model.cycles[boundary]
        )

    model.stored[0].fix(problem.battery.state.stored_energy_mwh)
    model.energy_balance = pyo.Constraint(model.steps, rule=energy_balance)
    model.usable_volume = pyo.Constraint(model.boundaries, rule=usable_volume)


def _add_lifetime_constraints(model: Any, problem: DispatchProblem) -> None:
    lifetime_cycles = problem.battery.spec.lifetime_cycles
    calendar_boundary = problem.calendar_end_boundary

    def cycle_balance(model: Any, step: int) -> Any:
        discarded = model.discarded_cycles if step + 1 == calendar_boundary else 0
        return (
            model.cycles[step + 1]
            == model.cycles[step]
            + drained_cycles(model, problem, step)
            - lifetime_cycles * (model.replaced[step + 1] - model.replaced[step])
            - discarded
        )

    def replacements_accumulate(model: Any, step: int) -> Any:
        return model.replaced[step + 1] >= model.replaced[step]

    model.cycles[0].fix(problem.battery.state.cycles_used)
    model.replaced[0].fix(0)
    model.cycle_balance = pyo.Constraint(model.steps, rule=cycle_balance)
    model.replacements_accumulate = pyo.Constraint(model.steps, rule=replacements_accumulate)

    if calendar_boundary is not None:
        replaced_before = model.replaced_before_calendar_end
        replaced_at_boundary = model.replaced[calendar_boundary]
        model.calendar_only_if_not_replaced = pyo.Constraint(
            expr=replaced_before <= replaced_at_boundary
        )
        model.calendar_skipped_if_replaced = pyo.Constraint(
            expr=replaced_before >= replaced_at_boundary / problem.replacement_bound
        )
        model.calendar_discards_cycles = pyo.Constraint(
            expr=model.discarded_cycles <= lifetime_cycles * (1 - replaced_before)
        )
        model.calendar_resets_cycles = pyo.Constraint(
            expr=model.cycles[calendar_boundary] <= lifetime_cycles * replaced_before
        )

    if problem.cycle_cap is not None:
        model.cycle_pace = pyo.Constraint(
            expr=sum(drained_cycles(model, problem, step) for step in model.steps)
            <= problem.cycle_cap
        )


def _add_objective(model: Any, problem: DispatchProblem) -> None:
    market_profit = sum(
        market.interval_hours
        * (
            market.sell_prices_gbp_per_mwh[interval] * model.discharge[index, interval]
            - market.buy_prices_gbp_per_mwh[interval] * model.charge[index, interval]
        )
        for index, market in enumerate(problem.markets)
        for interval in range(market.interval_count)
    )
    replacements = model.replaced[problem.base_step_count]
    if problem.calendar_end_boundary is not None:
        replacements = replacements + (1 - model.replaced_before_calendar_end)
    spec = problem.battery.spec
    battery_value_end = battery_value_gbp(spec, model.cycles[problem.base_step_count])
    model.profit = pyo.Objective(
        expr=market_profit - spec.capex_gbp * replacements + battery_value_end,
        sense=pyo.maximize,
    )
