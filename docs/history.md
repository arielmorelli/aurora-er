# Project history

How the project is being built, step by step: what was asked, what was decided, and what changed along the way. Formal decisions live in [ADRs](adr/); this is the narrative around them. Newest entries at the bottom.

## 2026-10-04

### 1. Project scaffold

- Started from the exercise brief and data in `docs/input/` (battery dispatch across two wholesale markets).
- Chose a src-layout Python package (`src/aurora_er/`) with unit tests in `tests/`; integration and e2e tests left out of scope.
- Made `docs/` the source of truth and added `CLAUDE.md` so the AI assistant reads the docs before changing anything → [ADR 0001](adr/0001-project-structure-and-ai-usage.md).
- uv, ruff, mypy, pytest and pre-commit were a fixed requirement, so they were recorded as a single decision → [ADR 0002](adr/0002-python-tooling.md).
- Python 3.12 picked as minimum to match the local interpreter (uv defaulted to 3.14).
- mypy runs in strict mode; pre-commit hooks call `uv run` so they use the versions pinned in `uv.lock`.

### 2. Makefile and commit convention

- Added a Makefile as the single command interface: `make install`, `run`, `test`, `check` → [ADR 0003](adr/0003-makefile-as-command-interface.md).
- `make check` delegates to pre-commit, so the local check and the commit hook are the same thing.
- `make run` needed a target, so a placeholder `python -m aurora_er` entry point was added.
- Adopted Conventional Commits, enforced by a `commit-msg` hook → [ADR 0004](adr/0004-conventional-commits.md).
- First commit: `chore: scaffold project structure, tooling and ADRs`.

### 3. Battery parameters DTO

- Modelled `Attachment 1.xlsx` as `BatterySpecDTO`: a frozen dataclass used as a DTO for the future transport layer, independent of the xlsx format → [ADR 0005](adr/0005-dtos-as-frozen-dataclasses.md) (Proposed).
- Options considered: field names mirroring the sheet vs. unit-suffixed names; `dto/` vs. `transport/` package. Chose unit-suffixed names in `dto/`.
- The sheet labels charging/discharging "efficiency" but the values (0.05) are losses, so the fields became `charging_loss_fraction` / `discharging_loss_fraction`.
- `kw_only=True` so same-typed fields (e.g. charge vs. discharge rate) can't be swapped positionally.

### 4. Code style

- First stated as "clean code, comments only when extremely necessary"; all comments and docstrings were removed.
- Clarified: **docstrings are required, only `#` comments are restricted**. Docstrings were restored → [code style guideline](guidelines/code-style.md).

### 5. Market DTO

- Modelled Market 2 (`Attachment 2.xlsx`, hourly sheet) as `MarketDTO`, generic enough to also hold Market 1 (half-hourly).
- Requirement: a horizon (start inclusive, end exclusive) and a step length. Prices are a plain tuple; the price at index `i` covers the interval starting at `horizon_start + i * step_length`.
- Added `name` to tell markets apart.
- Data inspection found timestamp quirks to handle in the loader, not the DTO:
  - Market 2: 6 timestamps a few milliseconds off the hour (Excel float precision), e.g. `2020-12-31 22:59:59.994`.
  - Market 1: 3 gaps of 90 min and 3 steps back of 30 min (likely DST artefacts).
  - The fixed grid (start + step) lets the loader snap to it rather than trust each timestamp.

### 6. Solver choice

- Requirement from the author: Pyomo + HiGHS, with the ADR discussing the alternatives (OR-Tools and others) → [ADR 0006](adr/0006-optimisation-modelling-and-solver.md).
- Framed the problem first: continuous power/SoC decisions with linear constraints, plus "no simultaneous charge and discharge", which needs binaries because both markets have negative prices → MILP.
- Compared approaches (heuristic, dynamic programming, MILP), modelling layers (Pyomo, OR-Tools, PuLP, linopy, CVXPY, SciPy, python-mip) and solvers (HiGHS, CBC, GLPK, SCIP, commercial). Main criterion: reviewers reproduce results with `make install` alone.
- Added `pyomo` and `highspy` as runtime dependencies; verified a small MILP solves through Pyomo's HiGHS interface.
- Pyomo has no type information, so mypy skips it; Pyomo is to stay confined to the optimisation module behind DTOs.
- Full-horizon size (~250k variables, ~50k binaries) flagged; rolling horizon deferred to a later ADR if needed.

### 7. Problem definition

- The author described the solver interface; each point was checked against the brief before being documented → [problem definition](problem-definition.md), [ADR 0007](adr/0007-battery-dispatch-formulation.md).
- Single entry point `solve(battery, horizon, markets, options)`; the new `BatteryDTO` combines the static spec with the current state.
- Output: split charge/discharge per market on its own step, stored energy on the finest grid, profit breakdown, `final_state` to chain windows, errors raised instead of returned.
- Degradation: the author asked whether it should be per step — yes, and it stays linear.
- Lifetime: the author rejected a cost per cycle. Instead, reaching the cycle (or calendar) limit triggers a replacement costing the capex again.
- The pro-rated cycle cap was first proposed as a rule, then questioned by the author ("how do you know it should last 10 years?"). Attachment 1 only gives maximums, so the cap became a required option, not a rule.
- New project rule from the author: **no hard-coded values**; everything comes through DTOs, which have no defaults.
- Other decisions: opex per operating year started; cycles counted on energy out of storage; a replacement keeps stored energy; separate buy/sell prices per market; `MarketDTO` keeps its own horizon fields.
- End-of-horizon stored energy left as an open question.

### 8. Timezones

- New project rule from the author: **every `datetime` must be timezone-aware**. Added to the code style guideline, `CLAUDE.md`, the problem definition (input validation) and ADR 0007.
- The spreadsheets have naive timestamps, so the loader must attach a zone. Market 1's 90-minute gaps and 30-minute steps back look like UK clock changes, which suggests local UK time; to be confirmed when writing the loader.

### 9. DTO validation

- The author asked for validation on DTOs wherever possible, reversing the "no validation in DTOs" rule of ADR 0005 (still Proposed, so amended in place).
- Each DTO checks its own invariants in `__post_init__` and raises `InvalidDTOError`; checks spanning several DTOs stay in `solve()`.
- Negative prices are explicitly allowed: both markets have them.

### 10. Solver implementation

- Implemented the problem definition in `aurora_er.solver`: cross-DTO validation → numeric problem on a base grid → Pyomo MILP → injected backend (`HighsBackend`) → result DTOs. Pyomo is confined to this package.
- Added the remaining DTOs (`HorizonDTO`, `BatteryStateDTO`, `BatteryDTO`, `SolveOptionsDTO`, result DTOs) and split market prices into buy/sell.
- Found while implementing: subtracting two datetimes in the same `ZoneInfo` uses wall-clock time, so durations across a clock change were an hour off. All duration maths now goes through `aurora_er.timing` (UTC-based).
- `solve` gained a `backend` argument (dependency injection), so status and failure paths are tested with fake backends.
- Tests solve small hand-checkable instances with real HiGHS: losses, the brief's two-market example, hourly commitment, no simultaneous charge/discharge across markets, degradation, cycle and calendar replacement, cycle pace.

### 11. Tests on the provided data

- The author asked for a test that feeds the real inputs to the solver, with values copied from the spreadsheets into the code.
- Chose the first week of January 2018 (336 half-hourly + 168 hourly prices): the full three years would be ~79k hard-coded values and a slow solve, and January is UTC in the UK, so the timestamps need no DST handling. The week was checked for timestamp gaps first.
- Added an independent checker that recomputes the brief's rules from a result (power limits, no simultaneous charge/discharge, energy balance with losses, degraded volume, revenue) and tests for the checker itself.
- First real-data result: £1,239.53 market profit over the week (21.6 cycles); £1,109.84 with the cycle pace cap (9.6 cycles). Both pinned as regression values.
- The two week-long solves take ~15 s, which now dominates `make check`.

### 12. Valuing battery wear

- The author asked whether the solver finds the best balance between profit and cycle use. It did not: within a horizon, cycles were free unless they crossed the lifetime, and the pace cap only imposed a fixed budget.
- On the real week the uncapped run spent ~£100 of battery life per cycle to earn ~£11.
- Fix → [ADR 0008](adr/0008-valuing-battery-wear.md): the battery is worth its capex in proportion to its remaining cycles, and the objective includes its end value, so each cycle costs capex / lifetime cycles. The author noted this equals the earlier-rejected cost per cycle; it is now derived from inputs and the replacement rule rather than assumed.
- ADR 0007 was accepted and committed, so it is superseded in part by ADR 0008 rather than edited.
- Real week after the fix: 6.5 cycles, £973.82 market profit, £321 after wear (vs −£923 uncapped and +£152 capped before). The pace cap no longer binds, and the suite runs in ~2 s instead of ~17 s.
- Found a tie: a battery ending exactly at its cycle limit may or may not be replaced at the last boundary (cost and restored value cancel). Documented; tests avoid that edge.

### 13. Attribution and docstring style

- New rules from the author: no AI co-author or attribution in commits, PRs, comments or docs; docstrings use single backticks. Added to `CLAUDE.md` and the code style guideline.
- The branch history (not yet pushed) was rewritten to remove the co-author trailers; file contents were verified unchanged.

### 14. First end-to-end run

- The author confirmed wiring is "just call `solve` with the right args" and asked for `make run-example`: read `inputs/` with pandas, build the DTOs, run, print → [ADR 0009](adr/0009-input-loading-and-run-configuration.md) (Proposed).
- Moved the exercise inputs from `docs/input/` to `inputs/` at the repo root.
- Every value of a run lives in a TOML config (`inputs/example.toml`), keeping the "no hard-coded values" rule.
- Correction to step 5: the market data is **not** UK local time. Every day has exactly 48/24 rows, so both sheets are a UTC grid; Market 1's March anomalies are 6 mislabelled rows (01:00/01:30 written as 02:00/02:30). The loader trusts row order and reports those rows in every run.
- Timing: one week ~1 s, one month ~5 s, a quarter > 10 min. The example runs January 2018; the full horizon needs windowing.
- First example result (January 2018): £4,015 market profit, 25.6 cycles, mostly buying in Market 1 and selling in Market 2.

### 15. Rolling monthly windows and JSON configuration

- The author asked for rolling windows with months as the base → [ADR 0010](adr/0010-rolling-monthly-windows.md): consecutive, non-overlapping calendar-month windows, each starting from the previous final state.
- Combined results are a new `RollingDispatchResultDTO`; the summary says "every window optimal" rather than "optimal", since windows do not see each other's prices.
- Chaining exposed solver tolerances: a final state a hair outside its bounds would fail the next window's validation, so it is clamped.
- The author replaced the TOML config with **JSON**, so a future UI can produce it; the example still reads and parses the spreadsheets on every run.
- Look-ahead between windows and a value for stored energy at window ends are left as improvements.
- First full run (2018–2020, 36 monthly windows, ~3.5 min, every window optimal): £124,950 market profit, 701 cycles, no replacements; after £500k capex, £15k opex and £429,861 of battery value left, net £39,811. Almost all profit comes from buying in Market 1 and selling in Market 2.
- Correction from the author: `inputs/` holds only the given problem, so there is no example config file. `make run-example` runs `aurora_er.example`, which reads the spreadsheets on the fly and hard-codes the values they lack (file locations, timezone, battery state, horizon, solver limits) in that script only. The JSON reader stays for future UI-driven runs.
- The author removed the JSON reader as well: there is no configuration file at all. `RunConfig` stays as the dataclass the example script builds; the `python -m aurora_er` entry point and `make run` are removed.

### 16. User interface framework

- The author proposed Streamlit for a UI and asked whether a lighter framework would be better → [ADR 0011](adr/0011-user-interface-framework.md) (Proposed).
- Compared Streamlit, NiceGUI, Gradio, Dash, Panel, Shiny for Python, marimo and a custom FastAPI frontend against framework criteria: Python only, light, built-in components, long-running calls, mypy strict, browser-free tests and familiarity.
- Recommended Streamlit (built-in components, widely known, `AppTest` for pytest); NiceGUI as the fallback if the script re-run model gets in the way.

### 17. Documentation line breaks

- New rule from the author: never break a sentence across lines in documents → [documentation guideline](guidelines/documentation.md).
- Every Markdown file was unwrapped to one line per paragraph or list item; a script checked that each file kept exactly the same words.
- The author pointed out the ADR mixed in UI behaviour (run button, progress); it was narrowed to the framework choice only, with UI design left for later. The UI will have no progress bar.

### 18. UI design

- The author accepted ADR 0011 (Streamlit) and described the UI: a Run tab (form, uploads, template download) and a History tab (sessions, cancel, result, rerun), with runs stored as session folders and executed in a background thread.
- Drafted [UI design](ui-design.md) with open questions: cancelling a thread, rerun semantics, template layout, editable market definitions, stale sessions after a server stop, week alignment, concurrent runs.
- Added on request: a "Fill with example" button that loads the provided attachments and example values, and a window size choice of day, week, month or 3 months (amends ADR 0010).

### 19. UI implementation

- The author approved the mockup and asked to implement it. The mockup followed the recommendations on the open questions, so they were adopted → [ADR 0013](adr/0013-sessions-and-background-runs.md), [UI design](ui-design.md).
- Window sizes day, week, month and 3 months replace `months_per_window` → [ADR 0012](adr/0012-window-sizes.md).
- `aurora_er.attachments` holds the Attachment layout once; the example script, the UI form and the download templates all use it.
- Writing the template tests found a loader gap: an empty battery value came through as NaN and failed later with a misleading message; it is now reported as "has no value".
- `aurora_er.sessions` (no Streamlit) stores sessions as folders with `config.yaml`, `status`, `result.json` and a `cancel` marker; runs are daemon threads; cancelling is cooperative between windows; running sessions are marked `interrupted` when the app starts.
- `aurora_er.ui` is a Streamlit app (`make ui`) tested with `AppTest`, including a run that starts from the form and finishes in its background thread.
- On request, `make run` starts the Streamlit UI (it was `make ui`); `make run-example` still runs the command-line example.
- Fixed a Streamlit warning seen in the live app ("widget … created with a default value but also had its value set via the Session State API"): widget defaults now live in one `_init_state` and widgets take no `value=`; a test fails on the old code.
- Look and layout changes from the author: blue instead of red, larger font (`.streamlit/config.toml`), Run at the top right, "Fill with example" and the downloads on separate lines, and a centred page switcher instead of left-aligned tabs (Streamlit tabs cannot be centred, so a required `segmented_control` switches pages).
- The author asked how a market's step is defined, since it is not in the file. Now each sheet of the uploaded prices spreadsheet is listed with its price column and a required step choice (15 min, 30 min, 1 hour); "Fill with example" presets Attachment 2's steps. The uploaders got tooltips describing the expected layout.
- While testing the step table, found that a select box without `index=None` silently falls back to its first option, so a fresh upload would have defaulted to 15 min. An explicit "Choose" option represents "not chosen", which also avoids the session-state warning `index=None` would bring back.
- History went back to the mockup layout on request: sessions listed on the left, the selected one on the right (the dropdown is gone).
- A UI test that started a rerun left its solve running into the next test, causing a rare error; it now waits for the run to finish.
- On request, every field and button on the Run page got an info tooltip explaining its meaning and rules (e.g. what the MIP gap and window sizes do, why the start must fall on a step boundary); a test checks no field is left without one.
- On request, a Run that passes validation now switches to History with the new session selected; a failed validation stays on Run with its errors.

### 20. Runs in processes

- The author hit a crash in the live app with two runs at once: Pyomo's HiGHS interface redirects the process-wide standard output and file descriptors during every solve, so solves in two threads collide. A multi-thread test reproduced it (deadlock).
- On the author's request, runs moved from threads to separate processes ("spawn") → [ADR 0014](adr/0014-background-runs-in-processes.md).
- Moving to "spawn" exposed a second bug: the child re-imported `app.py` as the main script and re-ran the app, marking the new session as interrupted. The app's `main()` is now guarded by `if __name__ == "__main__":`; a test fails without the guard.
- On request, the session summary line in History shows only the horizon dates, window size and status (no session id).
- Added `make clean`: deletes `sessions/`, tool caches, `__pycache__` folders and build output; keeps `.venv` and everything tracked by git.
- On request, a notice under the title says the UI is a prototype and that stopping the app stops running sessions.

### 21. Production architecture and next steps

- The author accepted ADR 0009.
- The author described how this would run in production: an API (FastAPI) that validates requests and stores them in a database (RDS) and blob storage (S3), a queue (SQS or RabbitMQ) carrying the run id, inputs and file ids, and isolated workers that run and report status back to the API; the UI talks only to the API → [production architecture](production-architecture.md).
- The document is explicit that the UI was mostly AI-generated and that its run machinery is a local prototype, maps each production component to the code that already does that step (`validation_errors`, `RunConfig`, `run_session`, `app.run`, the result serialisation), and lists what still has to change, starting with extracting interfaces from the folder-based `SessionStore`.
