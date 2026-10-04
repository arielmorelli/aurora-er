# aurora-er

A Python project that models a battery charging and discharging across wholesale electricity markets to maximise profit. It was built as a technical exercise for a recruitment process; the brief and the data are in [`inputs/`](inputs/), and the results for that data are in [`docs/results.md`](docs/results.md).

## Approach

The battery's decisions are a mixed-integer linear program (MILP) written in Pyomo and solved with HiGHS. For every market interval it chooses how much power to buy or sell in each market, under the brief's rules: shared charge and discharge limits across markets, capacity committed for a whole market interval, no charging and discharging at the same time, losses on the way in and out, and storage bounded by a volume that shrinks with every cycle. Battery wear is priced: the battery is worth its capex in proportion to the cycles it has left, so the solver only cycles when a price spread pays for the wear, and a battery that reaches its cycle or calendar lifetime is replaced at full capex. Three years of half-hourly data are too large for one model, so the horizon is solved in consecutive windows (a day, a week or a month), each starting from the previous window's battery state. Every input is a validated, immutable DTO; nothing in the model is hard-coded. The reasoning behind each choice is recorded in [`docs/adr/`](docs/adr/), and the full formulation in [`docs/problem-definition.md`](docs/problem-definition.md).

## Quick start

Requires [uv](https://docs.astral.sh/uv/) and GNU Make.

```bash
make help          # list every target (same as plain `make`)
make install       # create .venv, install dependencies and git hooks
make run-example   # solve the provided data (2018–2020, monthly windows) and print the results
make run           # open the web UI (Streamlit); runs are stored in sessions/
make test          # run the unit tests
make check         # lint, format, type-check and test everything
make ui-clean      # delete generated files: UI sessions, caches, build output
```

## Results

**Results for the provided inputs: [`docs/results.md`](docs/results.md)**, recorded with the date and commit they come from.

To reproduce them, `make run-example` solves the provided data (2018 to 2020) for an empty, new battery in monthly windows and prints the profit breakdown, the energy traded per market and the battery's final state. The run is deterministic, so the same code and inputs give the same figures.

## Tests

The project has only unit tests, run by `make test` and on every commit. There are no separate integration or end-to-end suites, because for this application the unit tests already cover the full path from the provided files to the result:

- **Real data through the solver:** the battery from Attachment 1 and the first week of both markets from Attachment 2, solved to optimality, with every rule of the brief re-checked independently on the result.
- **The example run:** `make run-example`'s configuration reads the provided spreadsheets and solves a day of them.
- **The UI:** Streamlit's `AppTest` drives the app headless: fill the form with the example, press Run, and wait for the run to finish in its own process with status `done`; History, cancel and rerun are covered the same way.
- **Hand-checked models:** small instances whose optimal answer is worked out by hand (losses, the brief's two-market example, hourly commitment, degradation, replacements, three markets).

## Markets

The model handles any number of markets, each with its own step, as long as every step is a whole multiple of the shortest one (for example 15 minutes, 30 minutes and 1 hour).

## Web UI

`make run` opens a prototype UI for running the model without code: upload the spreadsheets (or press "Fill with example"), set the battery state, horizon, window size and solver options, and follow runs in History. It is meant for local use; stopping it stops any running sessions. How it would work in production (an API, a queue and isolated workers) is described in [`docs/production-architecture.md`](docs/production-architecture.md).

## Project layout

```
src/aurora_er/
├── dto/             # validated, immutable inputs and results
├── loading/         # read the spreadsheets into DTOs
├── solver/          # MILP model, HiGHS backend, rolling windows
├── sessions/        # UI runs: session folders, background worker
├── ui/              # Streamlit app
├── example.py       # make run-example
└── attachments.py   # layout of the provided spreadsheets, templates
tests/               # unit tests
inputs/              # exercise brief and data (read-only)
docs/                # ADRs, guidelines, design, history — start here
```

See [`docs/README.md`](docs/README.md) for the documentation index, and [`docs/history.md`](docs/history.md) for how the project was built step by step.
