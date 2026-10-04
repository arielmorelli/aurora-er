"""Human-readable summary of a dispatch run."""

from collections.abc import Sequence

from aurora_er.dto import DispatchResultDTO, RollingDispatchResultDTO
from aurora_er.loading import LoadedMarket
from aurora_er.timing import in_hours


def format_window(window: DispatchResultDTO) -> str:
    """One line per solved window: period, status, profit and cycles."""
    return (
        f"{window.horizon.start.date().isoformat()} -> {window.horizon.end.date().isoformat()}"
        f"  {window.status.value:<8}"
        f"  market £{window.market_profit_gbp:>10,.2f}"
        f"  cycles {window.cycles_used_in_horizon:>6.2f}"
    )


def format_summary(result: RollingDispatchResultDTO, loaded_markets: Sequence[LoadedMarket]) -> str:
    """Totals of a run: status, money, energy per market, battery wear and input warnings."""
    optimality = (
        "every window optimal" if result.all_optimal else "some windows stopped at the time limit"
    )
    worst_gap = max(window.mip_gap for window in result.windows)
    lines = [
        f"Battery dispatch {result.horizon.start.isoformat()} -> {result.horizon.end.isoformat()}",
        f"{len(result.windows)} windows, {optimality} (worst MIP gap {worst_gap:.4%})",
        "",
        f"{'Market':<12}{'Charged MWh':>14}{'Discharged MWh':>16}{'Profit £':>14}",
    ]
    for name, charged, discharged, profit in market_totals(result):
        lines.append(f"{name:<12}{charged:>14,.2f}{discharged:>16,.2f}{profit:>14,.2f}")
    lines += [
        "",
        f"Market profit         £{result.market_profit_gbp:>14,.2f}",
        f"Capex                -£{result.capex_gbp:>14,.2f}",
        f"Opex                 -£{result.opex_gbp:>14,.2f}",
        f"Battery value start  -£{result.battery_value_start_gbp:>14,.2f}",
        f"Battery value end    +£{result.battery_value_end_gbp:>14,.2f}",
        f"Net profit            £{result.net_profit_gbp:>14,.2f}",
        "",
        f"Cycles used: {result.cycles_used_in_horizon:,.2f}  Replacements: {result.replacements}",
        f"Final state: {result.final_state.stored_energy_mwh:.2f} MWh stored, "
        f"{result.final_state.cycles_used:,.2f} cycles, "
        f"commissioned {result.final_state.commissioned_at.isoformat()}",
    ]
    lines += timestamp_warnings(loaded_markets)
    return "\n".join(lines)


def timestamp_warnings(loaded_markets: Sequence[LoadedMarket]) -> tuple[str, ...]:
    """One warning per market with misplaced timestamps, followed by one line per row."""
    lines: list[str] = []
    for loaded in loaded_markets:
        if loaded.misplaced:
            lines.append(
                f"Warning: {loaded.market.name} has {len(loaded.misplaced)} rows whose "
                "timestamp does not match their position; their position was used:"
            )
            lines += [
                f"  row {entry.row}: recorded {entry.recorded.isoformat()}, "
                f"slot {entry.expected.isoformat()}"
                for entry in loaded.misplaced
            ]
    return tuple(lines)


def market_totals(result: RollingDispatchResultDTO) -> list[tuple[str, float, float, float]]:
    """Per market across all windows: name, MWh charged, MWh discharged, profit."""
    totals: dict[str, list[float]] = {}
    for window in result.windows:
        for market in window.markets:
            hours = in_hours(market.step_length)
            entry = totals.setdefault(market.name, [0.0, 0.0, 0.0])
            entry[0] += sum(market.charge_mw) * hours
            entry[1] += sum(market.discharge_mw) * hours
            entry[2] += market.profit_gbp
    return [
        (name, charged, discharged, profit)
        for name, (charged, discharged, profit) in totals.items()
    ]
