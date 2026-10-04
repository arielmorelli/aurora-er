# 0007. Battery dispatch formulation

- **Status:** Accepted; battery lifetime costing superseded by [0008](0008-valuing-battery-wear.md)
- **Date:** 2026-10-04

## Context

[ADR 0006](0006-optimisation-modelling-and-solver.md) chose a MILP in Pyomo solved with HiGHS. This ADR records how the problem is framed: the solver's interface, how the battery's lifetime is accounted for, and which rules beyond the brief are modelled. The full specification is in [`docs/problem-definition.md`](../problem-definition.md).

## Decision

### Interface

- **One entry point** receives everything as arguments: `solve(battery, horizon, markets, options, backend) -> DispatchResultDTO`. The optimisation backend is injected, so tests can replace it.
- **No hard-coded values.** Every number comes from a DTO; DTOs have no default field values, so every input is explicit at the call site. Only unit conversions are constants in code.
- **Every `datetime` is timezone-aware**, in inputs and outputs. Naive datetimes are rejected by input validation; mixing naive and aware values would otherwise fail at comparison time or silently misalign markets recorded in different zones.
- **`BatteryDTO` = `BatterySpecDTO` + `BatteryStateDTO`.** The spec is static; the state (stored energy, cycles used, commissioning date) changes between runs and is returned as `final_state`, so windows can be chained.
- **`HorizonDTO(start, end)`** is the window to optimise. `MarketDTO` keeps its own `horizon_start`/`horizon_end` for the data it carries; the solver slices each market to the horizon.
- **Markets are a list** of `MarketDTO`, each with its own step length, so the two markets in the brief are not special-cased.
- **Separate buy and sell prices** per market. Identical for the provided data, but a bid/ask spread needs no model change.
- **`SolveOptionsDTO`** is a required argument (cycle pace switch, time limit, MIP gap).

### Output

- Charge and discharge are separate non-negative series per market, on that market's own step, so they align index-by-index with its prices.
- Stored energy is reported on the finest grid, at every boundary.
- Profit is broken down into market profit, capex, opex and net.
- Invalid input and solver failure raise errors; the result only carries `OPTIMAL` or `FEASIBLE` (time limit reached with a solution).

### Battery lifetime and degradation

- **Cycles** are counted on energy leaving storage (before the discharge loss) against the nominal volume.
- **Degradation** is applied per step: usable volume shrinks linearly with cycles on the current battery.
- **End of life** is at `lifetime_years` or `lifetime_cycles`, whichever comes first; **each end of life costs `capex_gbp`** for a replacement. Cycles cost nothing until they trigger one.
- **A replacement keeps the stored energy** (instant swap, no downtime) and resets cycles and degradation.
- **Initial capex** counts when the battery is commissioned at the horizon start; **opex** counts once per operating year started in the horizon.
- **Cycle pace cap** is available as a required option: when on, cycles in the horizon are limited to the remaining cycles spread over the remaining calendar life.

## Alternatives considered

- **Cost per cycle in the objective** (capex / lifetime cycles = £100 per cycle). Common practice, but it turns the lifetime limit into an economic assumption. Rejected in favour of an explicit replacement cost when the limit is reached.
- **Mandatory pro-rated cycle cap.** Assumes the battery should reach its maximum calendar life, which Attachment 1 does not state (both lifetimes are maximums). Kept as an option rather than a rule.
- **Ignoring degradation and lifetime.** Allowed by the brief, but both are in the provided data and stay linear, so they are modelled.
- **Signed net power** instead of separate charge/discharge. More compact but needs a sign convention and does not extend to separate buy/sell prices.
- **Defaults on DTO fields** (e.g. solver time limit). Rejected: hidden values make results harder to reproduce.

## Consequences

- The model is a MILP with one binary per base step (no simultaneous charge and discharge) and one integer per boundary (replacements). Full three-year runs may need a windowed approach; a later ADR will decide.
- Every reported number traces back to an input DTO and a rule in the problem definition.
- Without the cycle pace cap, the optimiser may use a large share of the battery's cycles in a short horizon, because the replacement it causes can fall beyond the horizon. This is documented as a known limitation and is a discussion point for the results.
- End-of-horizon stored energy is unconstrained; this stays an open question.
