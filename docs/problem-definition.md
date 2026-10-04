# Problem definition

The battery dispatch problem the solver implements: inputs, rules, formulation and output. Every rule traces back to the brief (`inputs/2nd Round Technical Question.pdf`) or to the battery parameters (`inputs/Attachment 1.xlsx`). Decisions and rejected alternatives are in [ADR 0007](adr/0007-battery-dispatch-formulation.md); the modelling tool is in [ADR 0006](adr/0006-optimisation-modelling-and-solver.md).

No value is hard-coded: every number the model uses comes from an input DTO. The only constants in code are unit conversions (hours per timedelta, percent to fraction).

Every `datetime`, in inputs and outputs, is timezone-aware. Naive datetimes are rejected.

## Entry point

A single function receives everything as arguments:

```python
def solve(
    battery: BatteryDTO,
    horizon: HorizonDTO,
    markets: Sequence[MarketDTO],
    options: SolveOptionsDTO,
    backend: MilpBackend,
) -> DispatchResultDTO: ...
```

Long horizons are solved as consecutive windows (a day, a week, a month or three months) by `solve_rolling`, which calls `solve` once per window and chains the battery state ([ADR 0010](adr/0010-rolling-monthly-windows.md), [ADR 0012](adr/0012-window-sizes.md)).

`backend` is injected ([dependency injection](guidelines/code-style.md#dependency-injection)): `HighsBackend` in production, fakes in tests.

## Inputs

All DTOs are frozen, keyword-only dataclasses with no default values ([ADR 0005](adr/0005-dtos-as-frozen-dataclasses.md)).

```
BatteryDTO
├── spec: BatterySpecDTO            # static, from Attachment 1
│     ├── max_charging_rate_mw
│     ├── max_discharging_rate_mw
│     ├── max_storage_volume_mwh
│     ├── charging_loss_fraction
│     ├── discharging_loss_fraction
│     ├── lifetime_years
│     ├── lifetime_cycles
│     ├── degradation_rate_pct_per_cycle
│     ├── capex_gbp
│     └── fixed_operational_costs_gbp_per_year
└── state: BatteryStateDTO          # at horizon.start
      ├── stored_energy_mwh
      ├── cycles_used               # on the current battery
      └── commissioned_at           # when the current battery was installed

HorizonDTO
├── start                           # inclusive
└── end                             # exclusive

MarketDTO                           # one per market, from Attachment 2
├── name
├── horizon_start
├── horizon_end
├── step_length
├── buy_prices_gbp_per_mwh          # paid when charging
└── sell_prices_gbp_per_mwh         # received when discharging

SolveOptionsDTO
├── enforce_cycle_pace              # see "Optional: cycle pace"
├── time_limit_seconds
└── mip_gap
```

The brief gives one price per interval; for the provided data the buy and sell series are identical. They are separate so markets with a bid/ask spread need no model change.

## Rules

| # | Rule | Source |
| --- | --- | --- |
| R1 | The battery is a price taker | Brief |
| R2 | Capacity committed to a market is held for that market's whole interval | Brief |
| R3 | Revenue = power × interval hours × price (5 MW × 0.5 h × £50 = £125) | Brief |
| R4 | Total charging power across markets ≤ max charging rate | Brief, Attachment 1 |
| R5 | Total discharging power across markets ≤ max discharging rate | Brief, Attachment 1 |
| R6 | The same unit of energy cannot be sold into two markets | Brief |
| R7 | The battery cannot charge and discharge at the same time, across all markets | Brief |
| R8 | Stored energy stays between 0 and the usable volume | Brief, Attachment 1 |
| R9 | A fraction of imported energy is lost before storage | Attachment 1 |
| R10 | A fraction of energy leaving storage is lost before reaching the grid | Attachment 1 |
| R11 | One cycle = throughput of one full storage volume; partial cycles add up | Attachment 1 |
| R12 | Usable volume shrinks by `degradation_rate_pct_per_cycle` % per cycle | Attachment 1 |
| R13 | A battery's life ends at `lifetime_years` or `lifetime_cycles`, whichever comes first | Attachment 1 |
| R14 | Each end of life triggers a replacement costing `capex_gbp` | Author's decision on R13 |
| R15 | Purchase (`capex_gbp`) and `fixed_operational_costs_gbp_per_year` are costs | Attachment 1 |

Check against the brief's example: a 5 MW / 5 MWh battery committing 2 MW to Market 1 for two half-hours and 3 MW to Market 2 for one hour uses 2 + 3 = 5 MW at every instant (R5) and 2 × 1 h + 3 × 1 h = 5 MWh (R8, ignoring losses). Committing 5 MW to both would violate R5.

## Formulation

A mixed-integer linear program (MILP), solved with HiGHS through Pyomo.

### Time grid

- `δ` = the finest market step length; every market's step length must be a whole multiple of `δ`.
- Base steps `t = 0 … T−1` cover the horizon, `T = (end − start) / δ`. Boundaries `t = 0 … T` are the instants between them.
- `k(m, t)` = the interval of market `m` that contains base step `t`.
- `h(x)` = a duration `x` in hours.

### Parameters

| Symbol | DTO field |
| --- | --- |
| `Pc`, `Pd` | `max_charging_rate_mw`, `max_discharging_rate_mw` |
| `V` | `max_storage_volume_mwh` (nominal) |
| `ηc`, `ηd` | `charging_loss_fraction`, `discharging_loss_fraction` |
| `g` | `degradation_rate_pct_per_cycle / 100` |
| `Lc`, `Ly` | `lifetime_cycles`, `lifetime_years` |
| `X`, `O` | `capex_gbp`, `fixed_operational_costs_gbp_per_year` |
| `e0`, `z0` | `state.stored_energy_mwh`, `state.cycles_used` |
| `pb[m,k]`, `ps[m,k]` | `buy_prices_gbp_per_mwh`, `sell_prices_gbp_per_mwh` |
| `Δm` | `step_length` of market `m` |

### Variables

| Variable | Domain | Meaning |
| --- | --- | --- |
| `c[m,k]`, `d[m,k]` | ≥ 0 | Charging / discharging power committed to market `m`, interval `k` (grid side, MW) |
| `u[t]` | {0, 1} | 1 if the battery may charge in base step `t`, 0 if it may discharge |
| `e[t]` | ≥ 0 | Stored energy at boundary `t` (MWh) |
| `z[t]` | [0, Lc] | Cycles on the current battery at boundary `t` |
| `r[t]` | integer ≥ 0 | Cycle-driven replacements up to boundary `t` |
| `w` | {0, 1} | 1 if the initial battery is cycle-replaced before its calendar end of life (only when that falls in the horizon) |
| `s[t]` | ≥ 0 | Cycles discarded at boundary `t` with a battery replaced on calendar age |

Indexing `c` and `d` by market interval, not base step, enforces R2.

### Constraints

```
Power and exclusivity (R4, R5, R7), for every base step t:
  Σm c[m, k(m,t)] ≤ Pc ×      u[t]
  Σm d[m, k(m,t)] ≤ Pd × (1 − u[t])

Energy balance (R6, R9, R10), for every base step t:
  charged[t] = h(δ) × (1 − ηc) × Σm c[m, k(m,t)]      # into storage
  drained[t] = h(δ) / (1 − ηd) × Σm d[m, k(m,t)]      # out of storage
  e[t+1] = e[t] + charged[t] − drained[t]
  e[0]   = e0

Cycles (R11), counted on energy out of storage against the nominal volume:
  q[t]   = drained[t] / V
  z[t+1] = z[t] + q[t] − Lc × (r[t+1] − r[t]) − s[t+1]
  z[0]   = z0,  r[0] = 0,  r[t+1] ≥ r[t]
  0 ≤ z[t] ≤ Lc            # forces a replacement at Lc, forbids early ones

Usable volume and degradation (R8, R12), for every boundary t:
  e[t] ≤ V × (1 − g × z[t])

Calendar end of life (R13), only if commissioned_at + Ly falls in the horizon,
at its boundary tc (first boundary at or after that instant):
  w ≤ r[tc]                # w = 1 only if a cycle-driven replacement happened...
  w ≥ r[tc] / R            # ...and always if one did
  s[tc] ≤ Lc × (1 − w)     # cycles discarded with the old battery
  z[tc] ≤ Lc × w           # calendar replacement → new battery starts at 0
  s[t] = 0 for t ≠ tc
```

`R` bounds the number of cycle-driven replacements and is derived from the inputs, not hard-coded: the most cycles the battery could run in the horizon, `z0 + T × h(δ) × Pd / ((1 − ηd) × V)`, divided by `Lc`, rounded up (at least 1).

When the cycle limit is crossed mid-step, the excess cycles carry over to the new battery (`z` drops by exactly `Lc`); this is exact up to one base step.

### Objective

Battery wear is valued ([ADR 0008](adr/0008-valuing-battery-wear.md)): the installed battery is worth its capex in proportion to the cycles it has left.

```
battery_value(z)  = X × (Lc − z) / Lc

maximise  market_profit − replacement_capex + battery_value(z[T])

market_profit     = Σm Σk h(Δm) × (ps[m,k] × d[m,k] − pb[m,k] × c[m,k])
replacement_capex = X × (r[T] + (1 − w) × [tc in horizon])
```

Each cycle therefore costs `X / Lc` (£100 for Attachment 1): a cycle-driven replacement pays `X` but restores `X` of value, so it nets to zero, and a calendar replacement costs the value the old battery still had.

The remaining terms do not depend on the decisions and are added to the reported result only:

```
initial_capex       = X  if commissioned_at == horizon.start, else 0
opex                = O × number of operating years started in the horizon,
                      where operating year n starts at commissioned_at + n years (n ≥ 0)
battery_value_start = 0  if commissioned_at == horizon.start (bought in the horizon,
                      counted in initial_capex), else battery_value(z0)

net_profit = market_profit − capex − opex + battery_value_end − battery_value_start
```

Battery value ignores calendar age: an unused battery keeps its value until its calendar end of life, when the calendar replacement writes it off.

### Optional: cycle pace

When `options.enforce_cycle_pace` is true, cycles in the horizon are capped to the battery's remaining cycles spread evenly over its remaining calendar life:

```
Σt q[t] ≤ (Lc − z0) × h(end − start) / h(commissioned_at + Ly − start)
```

When false, cycles are limited by their wear cost and by R13/R14. With wear valued, the cap is a comparison tool rather than a necessity.

## Output

```
DispatchResultDTO
├── horizon: HorizonDTO
├── status: SolveStatus                      # OPTIMAL | FEASIBLE (time limit, gap > 0)
├── mip_gap: float
├── market_profit_gbp: float
├── capex_gbp: float                         # cash: initial purchase + replacements
├── opex_gbp: float
├── battery_value_start_gbp: float           # 0 if bought at horizon start
├── battery_value_end_gbp: float
├── net_profit_gbp: float                    # market − capex − opex + value end − value start
├── markets: tuple[MarketDispatchDTO, ...]   # same order as the input
│     ├── name: str
│     ├── step_length: timedelta
│     ├── charge_mw: tuple[float, ...]       # one per market step
│     ├── discharge_mw: tuple[float, ...]    # one per market step
│     └── profit_gbp: float
├── energy_step_length: timedelta            # δ
├── stored_energy_mwh: tuple[float, ...]     # T + 1 boundaries
├── cycles_used_in_horizon: float
├── replacements: int                        # cycle-driven + calendar
└── final_state: BatteryStateDTO             # at horizon.end, feeds the next window
```

Result DTOs carry no Pyomo objects.

## Input validation

**On DTO construction** ([ADR 0005](adr/0005-dtos-as-frozen-dataclasses.md)), raising `InvalidDTOError`, every check that needs only the DTO's own fields:

- `BatterySpecDTO`: rates and volume positive; loss fractions in `[0, 1)`; lifetimes positive; degradation not negative and leaving usable volume after `lifetime_cycles`; capex and opex not negative
- `MarketDTO`: non-blank name; timezone-aware horizon; `horizon_start < horizon_end`; positive step; horizon a whole number of steps; one finite price per step (negative prices allowed)
- New DTOs follow the same rule (e.g. `HorizonDTO`: aware and ordered; `BatteryStateDTO`: aware `commissioned_at`, non-negative energy and cycles; `SolveOptionsDTO`: positive time limit, gap in `[0, 1)`)

**In `solve()`**, before building the model, the checks that span DTOs:

- Every `datetime` is timezone-aware: `horizon.start`, `horizon.end`, each market's `horizon_start`/`horizon_end`, and `state.commissioned_at`
- `horizon.start < horizon.end`
- `markets` is non-empty and market names are unique
- Every market covers the horizon: `horizon_start ≤ start` and `end ≤ horizon_end`
- `start` and `end` fall on every market's interval boundaries (R2)
- Every market's `step_length` is a whole multiple of the finest one
- Every market's buy and sell series have one value per step of its own horizon
- `horizon.end − horizon.start ≤ lifetime_years` (at most one calendar end of life per horizon; a cycle-driven replacement cannot also age out within it)
- `commissioned_at ≤ horizon.start < commissioned_at + lifetime_years`
- `0 ≤ cycles_used ≤ lifetime_cycles`
- `0 ≤ stored_energy_mwh ≤ V × (1 − g × cycles_used)`

Valid inputs always have a feasible solution (doing nothing), so a solver failure is raised as an error rather than returned as a status.

## Open questions

- **Stored energy at the end of the horizon.** Not in the brief, so it is unconstrained: energy left in the battery has no value and the optimiser will sell it if profitable. With monthly windows this means each month tends to end empty.

## Known limitations

- **Tie at the cycle limit.** A battery that ends the horizon exactly at `lifetime_cycles` may or may not be replaced at the last boundary: the replacement costs `X` and restores `X` of value, so both are optimal.
- **Battery value is linear in cycles.** It ignores calendar age and the volume already lost to degradation.
- **Calendar replacement of a replaced battery** is not modelled; validation keeps the horizon within one calendar lifetime so it cannot occur.
