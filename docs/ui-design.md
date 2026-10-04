# UI design

- **Status:** Accepted (mockup approved by the author; layout may be adjusted in the live app)
- **Framework:** Streamlit ([ADR 0011](adr/0011-user-interface-framework.md))

## Overview

Two pages, switched with a centred control at the top of the page (only the selected page renders):

1. **Run** — fill a form (or fill it with the example), upload the spreadsheets, download a template, start a run.
2. **History** — list every run (session) with its status; open one to cancel it, see its result or rerun it.

Runs are file-based **sessions** in `sessions/` (git-ignored). The UI never solves anything itself: it validates, writes a session folder and starts a background process that does the work and records the outcome in files.

## Session folder

```
sessions/
└── 20261004T153012.123456Z/      # session_id: UTC creation time, microseconds avoid collisions
    ├── battery.xlsx              # uploaded battery parameters (Attachment 1 layout)
    ├── prices.xlsx               # uploaded market prices (Attachment 2 layout)
    ├── config.yaml               # every value the run needs besides the spreadsheets
    ├── status                    # running | done | cancelled | error + description | interrupted
    ├── result.json               # written only when the run is done
    └── cancel                    # present when cancelling was requested
```

- **`config.yaml`** holds what the example script hard-codes today: file names (relative to the session folder), sheets, price columns, timestamp timezone, step lengths, battery starting state, horizon, window size and solver options. Datetimes are ISO 8601 with an offset.
- **`status`** is plain text. The first line is the state; for `error`, the following lines hold the description. It is always replaced atomically (write a temporary file, then rename), so readers never see a half-written file.
- **`result.json`** is the full `RollingDispatchResultDTO` serialised to JSON, so History can show the same summary as `make run-example` and, later, charts.

## Look

- A notice under the title says the app is a prototype and that stopping it stops running sessions (they show as interrupted next time).
- Blue primary colour (no red accent), a larger base font and blue chart colours; set in `.streamlit/config.toml`, Streamlit's own config file, read when `make run` starts the app from the repository root.
- On the Run page, **Run** sits at the top right with its messages just below; **Fill with example** and the two template downloads are on separate lines.
- Every field and button on the Run page has an info tooltip: the uploaders describe the expected spreadsheet layout, the other fields explain what the value means and the rules it must follow.
- History lists sessions on the left (newest first, click to select) and shows the selected session on the right.

## Run tab

### Form

| Section | Fields |
| --- | --- |
| Files | Battery spreadsheet, prices spreadsheet (upload); "Download template"; "Fill with example" |
| Battery state | Stored energy (MWh), cycles used, commissioning date and time |
| Horizon | Start, end, window size: day, week or month |
| Solver | Enforce cycle pace (checkbox), time limit per window (s), MIP gap |

All datetimes are entered and stored in UTC.

### Fill with example

Copies `Attachment 1.xlsx` and `Attachment 2.xlsx` from `inputs/` into the upload folder, as if the user had uploaded them, and fills the form with the values `make run-example` uses (defined in `aurora_er.example`). The user can still change any field before running.

### Window size

The horizon is solved in consecutive windows of one **day**, **week** or **month**. Days and weeks are fixed lengths from the horizon start; months follow calendar months. This generalises `months_per_window` and amends [ADR 0010](adr/0010-rolling-monthly-windows.md), which only allows months; a new ADR records it when implemented.

### Upload

Uploaded files are written immediately to a temporary folder (one per browser session, created with `tempfile`), not to `sessions/`.

### Run button

1. **Validate:** parse both spreadsheets with the existing loaders, build the DTOs from the form, and run the solver's input validation (horizon inside the markets, battery commissioned and alive, etc.) without solving. Errors are shown next to the form and nothing is written to `sessions/`.
2. **Create the session:** new `sessions/<session_id>/`; move the files from the temporary folder; write `config.yaml`; write `status` = `running`.
3. **Start the worker** in a separate process ([ADR 0014](adr/0014-background-runs-in-processes.md)); the UI returns immediately, switches to History and selects the new session.

## Worker: `run_session(sessions_dir, session_id)`

Lives outside the UI (`aurora_er.sessions`), so it is tested without Streamlit.

1. Read `config.yaml` and the spreadsheets from the session folder.
2. Run `aurora_er.app.run` with `HighsBackend`.
3. On success: write `result.json`, then `status` = `done`.
4. On any exception: `status` = `error` plus the exception message.
5. On cancellation: `status` = `cancelled` (see question 1).

## History tab

- Lists every folder in `sessions/`, newest first, with its creation time (from the session id) and its status (every `status` file is read on each render).
- Selecting a session shows:
  - **running:** a "Cancel" button.
  - **done:** the result summary (profit breakdown, per-month table) and a "Rerun" button.
  - **error / cancelled:** the status text and a "Rerun" button.

## Code layout

```
src/aurora_er/
├── sessions/           # no Streamlit imports
│   ├── store.py        # create/list sessions, read/write status, config, result
│   ├── ids.py          # session ids from UTC time
│   ├── status.py       # status file format
│   ├── config_file.py  # RunConfig <-> config.yaml
│   ├── result_file.py  # RollingDispatchResultDTO <-> result.json
│   ├── launcher.py     # validation before saving, launch, rerun
│   └── worker.py       # run_session, run_in_background
├── attachments.py      # Attachment layout and download templates
└── ui/
    ├── form.py         # form values -> RunConfig, no Streamlit
    └── app.py          # Streamlit: tabs, form, history; wires the worker
```

- Launched with `make run`, which passes the sessions and inputs folders through the `AURORA_SESSIONS_DIR` and `AURORA_INPUTS_DIR` environment variables.
- The UI entry point also receives the `inputs/` folder, for "Fill with example".
- New dependencies: `streamlit`, `pyyaml` (+ `types-PyYAML` for mypy).
- Tests: `sessions` with plain pytest (temporary folders, small spreadsheets, fake backend); UI with Streamlit's `AppTest`.

## Decisions on the open questions

Taken from the approved mockup; architecture in [ADR 0013](adr/0013-sessions-and-background-runs.md).

1. **Cancel** is cooperative: a `cancel` marker file, checked by the worker after each window.
2. **Rerun** creates a new session with a copy of the old one's files and config.
3. **Templates:** one workbook per input (battery, prices) in the Attachment layout, generated from the loaders' expected layout.
4. **Market definitions:** each sheet of the prices spreadsheet with a timestamp and a price column is a market. The step is not in the file, so after upload the sheets are listed in a table where the user must choose each sheet's step from the options in `STEP_CHOICES` (`aurora_er.ui.form`); there is no default. Timestamps are read as UTC. (Replaces the earlier "fixed to the template layout".)
5. **Stale sessions** still marked `running` when the app starts are marked `interrupted`.
6. **Week windows** are 7 days counted from the horizon start ([ADR 0012](adr/0012-window-sizes.md)).
7. **Concurrent runs** are allowed.
