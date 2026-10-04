# 0006. Optimisation modelling and solver

- **Status:** Accepted
- **Date:** 2026-10-04

## Context

The battery must decide, for every interval, how much power to commit to
charging or discharging in each market so that profit is maximised
(see the brief in `docs/input/`). The rules map naturally onto a
mathematical program:

- **Continuous decisions:** charge/discharge power per market per interval,
  state of charge per interval.
- **Linear constraints:** power limits shared across markets, energy balance
  with charging/discharging losses, storage bounds, and Market 2 commitments
  held constant over each hour (two Market 1 half-hours).
- **One logical constraint:** the battery cannot charge and discharge at the
  same time. With negative prices (both markets go below zero in the data),
  an LP would profit from charging and discharging simultaneously to burn
  energy through losses, so this needs a **binary** per interval. The problem
  is therefore a **MILP**.
- **Size:** the full dataset is three years — 52,608 half-hourly and 26,304
  hourly prices. A single monolithic model has ~250k continuous variables and
  ~50k binaries; solving it in windows (e.g. a rolling horizon) may be needed.
  That is a modelling decision for a later ADR, but the tool must handle it.

Requirements for the tool, in priority order:

1. **Reproducible by reviewers with `make install` only** — free, open-source,
   pip-installable, no licence or system binary to set up.
2. Solves MILPs of the size above in reasonable time.
3. Readable model code: constraints should look like the maths, so reviewers
   can check them against the brief.
4. Solver-agnostic, so a faster solver can be swapped in without rewriting the
   model.
5. Mature and well documented.

## Options considered

### Approach

| Option | Assessment |
| --- | --- |
| Rule-based heuristic (e.g. charge below a price threshold, discharge above) | Allowed by the brief and simple, but not optimal, threshold tuning is arbitrary, and splitting power across two markets by hand gets complicated quickly. Useful as a **baseline** to compare against, not as the model. |
| Dynamic programming over discretised state of charge | Exact for one market, but two markets with continuous power split make the action space large, and discretisation loses precision. More bespoke code to review. |
| **Mathematical programming (LP/MILP)** | Matches the problem structure directly; optimal within the model; constraints are auditable against the brief. **Chosen.** |

### Modelling layer

| Option | Pros | Cons |
| --- | --- | --- |
| **Pyomo** | Algebraic modelling with indexed sets and parameters, so constraints read like the maths; solver-agnostic (HiGHS, CBC, SCIP, Gurobi, CPLEX…); mature, widely used in energy systems research; in-process HiGHS interface via `highspy`. | Model build is slower than vectorised tools on large instances; no type information (works against mypy strict); verbose API. |
| Google OR-Tools | Well-maintained, fast; `pywraplp`/MathOpt wrap GLOP, SCIP, CP-SAT and others; CP-SAT is excellent for scheduling. | LP/MILP API is lower-level and less expressive than Pyomo for indexed time series; CP-SAT needs integer coefficients (prices and losses would have to be scaled); smaller footprint in energy-market modelling. |
| PuLP | Very simple; bundles CBC; supports HiGHS. | No indexed sets/blocks, so larger models become ad-hoc dict manipulation; fewer features for decomposition or rolling-horizon reuse. |
| linopy | Vectorised (xarray), fast model build, used by PyPSA for power systems. | Younger, smaller community; ties the model to xarray; less familiar to most reviewers. |
| CVXPY | Clean expression syntax; strong for convex problems. | Built around convex (DCP) rules — mixed-integer support depends on the backend and is secondary to its purpose. |
| `scipy.optimize.milp` / `linprog` | Already uses HiGHS internally; no extra dependency beyond SciPy. | Matrix form only — every constraint is built by hand as rows of a sparse matrix, which is error-prone and hard to review. |
| python-mip | Fast, simple API with CBC. | Maintenance has slowed; fewer solver backends. |

### Solver

| Option | Assessment |
| --- | --- |
| **HiGHS** | MIT licence; installs with `pip install highspy` (no system binary); the strongest open-source LP solver and a competitive MIP solver; actively developed; also the default in SciPy. **Chosen.** |
| CBC | Open source (EPL) and long-standing, but slower on MIPs and usually needs a separate binary. |
| GLPK | Open source but markedly slower; not suited to this size. |
| SCIP | Strong open-source MIP solver (Apache 2.0), pip-installable via `pyscipopt`; a good fallback if HiGHS struggles on the MIP. |
| Gurobi / CPLEX / Xpress | Fastest MIP solvers, but commercial licences — reviewers could not reproduce results. Ruled out; Pyomo keeps the door open for local experimentation. |

## Decision

- Model the battery dispatch as a **MILP in Pyomo**, solved with **HiGHS**
  through the `highspy` Python package (Pyomo's in-process HiGHS interface).
- `pyomo` and `highspy` are runtime dependencies, pinned through `uv.lock`, so
  `make install` is enough to run the model — no external solver binary.
- **Pyomo is confined to the optimisation module(s).** Inputs arrive as DTOs
  ([ADR 0005](0005-dtos-as-frozen-dataclasses.md)) and results leave as typed
  objects; nothing outside the model builder touches Pyomo objects.
- Pyomo has no type information, so mypy is configured to skip it
  (`ignore_missing_imports` for `pyomo.*` in `pyproject.toml`). The confinement
  above keeps the untyped surface small.
- A simple rule-based strategy may be added later as a baseline for comparison,
  not as an alternative model.

## Consequences

- Reviewers get optimal (within the model) and reproducible results with no
  extra setup.
- Constraints can be read side by side with the brief.
- Switching to SCIP, CBC or a commercial solver is a configuration change.
- Model build time in Pyomo may dominate on the full three-year horizon; if
  so, the next step is a rolling-horizon or windowed formulation (separate
  ADR) before considering a faster modelling layer such as linopy.
- Code using Pyomo loses static type checking; it must be covered by unit
  tests on small, hand-checkable instances.
