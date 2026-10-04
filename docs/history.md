# Project history

How the project is being built, step by step: what was asked, what was
decided, and what changed along the way. Formal decisions live in
[ADRs](adr/); this is the narrative around them. Newest entries at the bottom.

## 2026-10-04

### 1. Project scaffold

- Started from the exercise brief and data in `docs/input/` (battery dispatch
  across two wholesale markets).
- Chose a src-layout Python package (`src/aurora_er/`) with unit tests in
  `tests/`; integration and e2e tests left out of scope.
- Made `docs/` the source of truth and added `CLAUDE.md` so the AI assistant
  reads the docs before changing anything → [ADR 0001](adr/0001-project-structure-and-ai-usage.md).
- uv, ruff, mypy, pytest and pre-commit were a fixed requirement, so they were
  recorded as a single decision → [ADR 0002](adr/0002-python-tooling.md).
- Python 3.12 picked as minimum to match the local interpreter (uv defaulted
  to 3.14).
- mypy runs in strict mode; pre-commit hooks call `uv run` so they use the
  versions pinned in `uv.lock`.

### 2. Makefile and commit convention

- Added a Makefile as the single command interface: `make install`, `run`,
  `test`, `check` → [ADR 0003](adr/0003-makefile-as-command-interface.md).
- `make check` delegates to pre-commit, so the local check and the commit hook
  are the same thing.
- `make run` needed a target, so a placeholder `python -m aurora_er` entry point
  was added.
- Adopted Conventional Commits, enforced by a `commit-msg` hook
  → [ADR 0004](adr/0004-conventional-commits.md).
- First commit: `chore: scaffold project structure, tooling and ADRs`.

### 3. Battery parameters DTO

- Modelled `Attachment 1.xlsx` as `BatterySpecDTO`: a frozen dataclass used as
  a DTO for the future transport layer, independent of the xlsx format
  → [ADR 0005](adr/0005-dtos-as-frozen-dataclasses.md) (Proposed).
- Options considered: field names mirroring the sheet vs. unit-suffixed names;
  `dto/` vs. `transport/` package. Chose unit-suffixed names in `dto/`.
- The sheet labels charging/discharging "efficiency" but the values (0.05) are
  losses, so the fields became `charging_loss_fraction` /
  `discharging_loss_fraction`.
- `kw_only=True` so same-typed fields (e.g. charge vs. discharge rate) can't be
  swapped positionally.

### 4. Code style

- First stated as "clean code, comments only when extremely necessary"; all
  comments and docstrings were removed.
- Clarified: **docstrings are required, only `#` comments are restricted**.
  Docstrings were restored → [code style guideline](guidelines/code-style.md).

### 5. Market DTO

- Modelled Market 2 (`Attachment 2.xlsx`, hourly sheet) as `MarketDTO`, generic
  enough to also hold Market 1 (half-hourly).
- Requirement: a horizon (start inclusive, end exclusive) and a step length.
  Prices are a plain tuple; the price at index `i` covers the interval starting
  at `horizon_start + i * step_length`.
- Added `name` to tell markets apart.
- Data inspection found timestamp quirks to handle in the loader, not the DTO:
  - Market 2: 6 timestamps a few milliseconds off the hour (Excel float
    precision), e.g. `2020-12-31 22:59:59.994`.
  - Market 1: 3 gaps of 90 min and 3 steps back of 30 min (likely DST
    artefacts).
  - The fixed grid (start + step) lets the loader snap to it rather than trust
    each timestamp.

### 6. Solver choice

- Requirement from the author: Pyomo + HiGHS, with the ADR discussing the
  alternatives (OR-Tools and others) → [ADR 0006](adr/0006-optimisation-modelling-and-solver.md).
- Framed the problem first: continuous power/SoC decisions with linear
  constraints, plus "no simultaneous charge and discharge", which needs
  binaries because both markets have negative prices → MILP.
- Compared approaches (heuristic, dynamic programming, MILP), modelling layers
  (Pyomo, OR-Tools, PuLP, linopy, CVXPY, SciPy, python-mip) and solvers
  (HiGHS, CBC, GLPK, SCIP, commercial). Main criterion: reviewers reproduce
  results with `make install` alone.
- Added `pyomo` and `highspy` as runtime dependencies; verified a small MILP
  solves through Pyomo's HiGHS interface.
- Pyomo has no type information, so mypy skips it; Pyomo is to stay confined
  to the optimisation module behind DTOs.
- Full-horizon size (~250k variables, ~50k binaries) flagged; rolling horizon
  deferred to a later ADR if needed.

### 7. Problem definition

- The author described the solver interface; each point was checked against
  the brief before being documented → [problem definition](problem-definition.md),
  [ADR 0007](adr/0007-battery-dispatch-formulation.md).
- Single entry point `solve(battery, horizon, markets, options)`; the new
  `BatteryDTO` combines the static spec with the current state.
- Output: split charge/discharge per market on its own step, stored energy on
  the finest grid, profit breakdown, `final_state` to chain windows, errors
  raised instead of returned.
- Degradation: the author asked whether it should be per step — yes, and it
  stays linear.
- Lifetime: the author rejected a cost per cycle. Instead, reaching the cycle
  (or calendar) limit triggers a replacement costing the capex again.
- The pro-rated cycle cap was first proposed as a rule, then questioned by the
  author ("how do you know it should last 10 years?"). Attachment 1 only gives
  maximums, so the cap became a required option, not a rule.
- New project rule from the author: **no hard-coded values**; everything comes
  through DTOs, which have no defaults.
- Other decisions: opex per operating year started; cycles counted on energy
  out of storage; a replacement keeps stored energy; separate buy/sell prices
  per market; `MarketDTO` keeps its own horizon fields.
- End-of-horizon stored energy left as an open question.

### 8. Timezones

- New project rule from the author: **every `datetime` must be
  timezone-aware**. Added to the code style guideline, `CLAUDE.md`, the
  problem definition (input validation) and ADR 0007.
- The spreadsheets have naive timestamps, so the loader must attach a zone.
  Market 1's 90-minute gaps and 30-minute steps back look like UK clock
  changes, which suggests local UK time; to be confirmed when writing the
  loader.

### 9. DTO validation

- The author asked for validation on DTOs wherever possible, reversing the
  "no validation in DTOs" rule of ADR 0005 (still Proposed, so amended in
  place).
- Each DTO checks its own invariants in `__post_init__` and raises
  `InvalidDTOError`; checks spanning several DTOs stay in `solve()`.
- Negative prices are explicitly allowed: both markets have them.

### 10. Solver implementation

- Implemented the problem definition in `aurora_er.solver`: cross-DTO
  validation → numeric problem on a base grid → Pyomo MILP → injected backend
  (`HighsBackend`) → result DTOs. Pyomo is confined to this package.
- Added the remaining DTOs (`HorizonDTO`, `BatteryStateDTO`, `BatteryDTO`,
  `SolveOptionsDTO`, result DTOs) and split market prices into buy/sell.
- Found while implementing: subtracting two datetimes in the same `ZoneInfo`
  uses wall-clock time, so durations across a clock change were an hour off.
  All duration maths now goes through `aurora_er.timing` (UTC-based).
- `solve` gained a `backend` argument (dependency injection), so status and
  failure paths are tested with fake backends.
- Tests solve small hand-checkable instances with real HiGHS: losses, the
  brief's two-market example, hourly commitment, no simultaneous
  charge/discharge across markets, degradation, cycle and calendar
  replacement, cycle pace.

### 11. Tests on the provided data

- The author asked for a test that feeds the real inputs to the solver, with
  values copied from the spreadsheets into the code.
- Chose the first week of January 2018 (336 half-hourly + 168 hourly prices):
  the full three years would be ~79k hard-coded values and a slow solve, and
  January is UTC in the UK, so the timestamps need no DST handling. The week
  was checked for timestamp gaps first.
- Added an independent checker that recomputes the brief's rules from a
  result (power limits, no simultaneous charge/discharge, energy balance with
  losses, degraded volume, revenue) and tests for the checker itself.
- First real-data result: £1,239.53 market profit over the week (21.6 cycles);
  £1,109.84 with the cycle pace cap (9.6 cycles). Both pinned as regression
  values.
- The two week-long solves take ~15 s, which now dominates `make check`.

### 12. Valuing battery wear

- The author asked whether the solver finds the best balance between profit
  and cycle use. It did not: within a horizon, cycles were free unless they
  crossed the lifetime, and the pace cap only imposed a fixed budget.
- On the real week the uncapped run spent ~£100 of battery life per cycle to
  earn ~£11.
- Fix → [ADR 0008](adr/0008-valuing-battery-wear.md): the battery is worth its
  capex in proportion to its remaining cycles, and the objective includes its
  end value, so each cycle costs capex / lifetime cycles. The author noted this
  equals the earlier-rejected cost per cycle; it is now derived from inputs and
  the replacement rule rather than assumed.
- ADR 0007 was accepted and committed, so it is superseded in part by ADR 0008
  rather than edited.
- Real week after the fix: 6.5 cycles, £973.82 market profit, £321 after wear
  (vs −£923 uncapped and +£152 capped before). The pace cap no longer binds,
  and the suite runs in ~2 s instead of ~17 s.
- Found a tie: a battery ending exactly at its cycle limit may or may not be
  replaced at the last boundary (cost and restored value cancel). Documented;
  tests avoid that edge.

### 13. Attribution and docstring style

- New rules from the author: no AI co-author or attribution in commits, PRs,
  comments or docs; docstrings use single backticks. Added to `CLAUDE.md` and
  the code style guideline.
- The branch history (not yet pushed) was rewritten to remove the co-author
  trailers; file contents were verified unchanged.
