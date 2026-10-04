# 0009. Input loading and run configuration

- **Status:** Accepted
- **Date:** 2026-10-04
- **Amends:** [ADR 0001](0001-project-structure-and-ai-usage.md) — exercise inputs move from `docs/input/` to `inputs/` at the repository root; [ADR 0003](0003-makefile-as-command-interface.md) — `make run` is replaced by `make run-example`

## Context

The solver takes DTOs; the provided data are spreadsheets. A first end-to-end run (`make run-example`) needs to read them, build the DTOs and print the result, without hard-coding any value ([ADR 0007](0007-battery-dispatch-formulation.md)).

Inspecting `Attachment 2.xlsx` showed:

- Every day has exactly 48 half-hourly and 24 hourly rows, including clock change days: both sheets are a regular **UTC** grid, not UK local time.
- On the three March clock-change days, Market 1's 01:00 and 01:30 rows are labelled 02:00 and 02:30 (their prices differ from the real 02:00 rows that follow): 6 mislabelled rows in total.
- Market 2 has timestamps a few milliseconds off the hour (Excel float precision) and trailing empty rows.

## Decision

- **`inputs/` at the repository root** holds only the given problem: the brief and the two spreadsheets. Nothing else is added there, and code never writes to it.
- **pandas** (with openpyxl) reads the spreadsheets, as required by the author. `pandas-stubs` keeps mypy strict.
- **Loaders live in `aurora_er.loading`**, one module per input. Each splits file reading (`read_*`) from a pure conversion (`*_from_frame`) so the conversion is tested on in-memory frames.
- **Battery sheet:** rows are matched by label to `BatterySpecDTO` fields and **units are checked**, so a unit change in the source fails loudly.
- **Market sheets: rows are trusted by position.** The grid is built from the first timestamp and the step length; each recorded timestamp is rounded to the step and compared with its slot. Rows that do not match are **reported** (`LoadedMarket.misplaced`) and printed as warnings, never silently fixed or dropped.
- **`make run-example` reads the spreadsheets and runs on the fly.** `aurora_er.example` reads and parses `inputs/` on every run. Values the spreadsheets do not contain (file and sheet names, price columns, the timezone timestamps are recorded in, step lengths, battery starting state, horizon, months per window, solver limits) are hard-coded in that example script only, never in the solver or loaders. It reads both sheets as UTC.
- **A `RunConfig` dataclass** carries those values into the composition root. There is no configuration file for `make run-example`; another data set or scenario is a new script, or a UI session, which stores its config as YAML ([ADR 0013](0013-sessions-and-background-runs.md)).
- **`aurora_er.app.run(config, backend, on_window_solved)`** is the composition root. The example wires `HighsBackend`, prints each window as it is solved, then the summary.
- **`make run-example` replaces `make run`** from [ADR 0003](0003-makefile-as-command-interface.md): the placeholder entry point it called is removed.
- The example covers all provided data (2018–2020) in monthly windows ([ADR 0010](0010-rolling-monthly-windows.md)).

## Consequences

- Running other data or scenarios means writing another small script; the loaders, solver and report are reused unchanged.
- Data problems are visible in every run's output instead of hidden in the loader.
- Trusting row order assumes the file has no missing or extra rows; the 48-per-day check above holds for the provided data, and any mismatch shows up as misplaced rows.
