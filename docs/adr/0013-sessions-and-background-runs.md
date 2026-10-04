# 0013. Sessions and background runs

- **Status:** Accepted; runs move from threads to processes in [0014](0014-background-runs-in-processes.md)
- **Date:** 2026-10-04

## Context

The UI ([ADR 0011](0011-user-interface-framework.md), [UI design](../ui-design.md)) starts runs that take minutes, must not block while they run, and must list past runs with their outcome. The author specified file-based sessions and a background thread per run.

## Decision

- **A session is a folder** `sessions/<session_id>/` (git-ignored). `session_id` is the UTC creation time to the microsecond (`20261004T153012.123456Z`), so ids sort by creation and do not collide.
- **Files in a session:**
  - `battery.xlsx`, `prices.xlsx`: the spreadsheets, in the Attachment layout.
  - `config.yaml`: everything else the run needs (battery state, horizon, window size, solver options, where the data is in the spreadsheets); spreadsheet paths are relative to the session folder.
  - `status`: plain text; the first line is `running`, `done`, `cancelled`, `error` or `interrupted`, followed by a description for errors. Always replaced atomically (write a temporary file, then rename).
  - `result.json`: the full `RollingDispatchResultDTO` plus input warnings, written only when the run is done.
  - `cancel`: present when cancelling was requested.
- **Uploads** go to a temporary folder per browser session; they move into a session only after the inputs pass validation (spreadsheets parsed, DTOs built, solver input checks), so invalid runs leave nothing behind.
- **Each run is a daemon thread** running `run_session(store, session_id, backend)`, which reads the session, solves, and writes the result and status. It never raises: errors become `status = error` with their description.
- **Cancelling is cooperative.** A Python thread cannot be killed, so Cancel writes the `cancel` marker and the worker stops after its current window. The delay is at most one window's solve (bounded by the time limit).
- **Rerun creates a new session** with a copy of the old one's spreadsheets and config, so history is never overwritten.
- **Interrupted runs:** when the app starts, sessions still marked `running` belong to a previous process that stopped; they are marked `interrupted`.
- **Several sessions may run at once.**
- The session code (`aurora_er.sessions`) has no Streamlit imports and is tested on its own; the thread starter and backend are injected.
- `make run` starts the UI; `make run-example` keeps running the example from the command line.
- New dependencies: `pyyaml` (and `types-PyYAML` for mypy).

## Alternatives considered

- **A process per run.** Could be stopped immediately, but the author asked for threads, and results would still need files to cross the process boundary.
- **A database (e.g. SQLite).** Cleaner for queries, but heavier than needed and less transparent than plain files a person can open.

## Consequences

- Sessions survive app restarts and can be inspected or deleted by hand.
- The History tab reads every `status` file on each render; fine for the expected number of sessions.
- Solving in threads shares one Python process; long CPU work in several sessions at once slows each other down.
