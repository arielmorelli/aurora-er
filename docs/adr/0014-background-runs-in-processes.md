# 0014. Background runs in processes

- **Status:** Accepted
- **Date:** 2026-10-04
- **Supersedes:** "Each run is a daemon thread" in [ADR 0013](0013-sessions-and-background-runs.md)

## Context

ADR 0013 ran each session in a daemon thread of the Streamlit process. In the live app, two runs at the same time (two sessions, or a rerun overlapping another run) crashed with:

```
RuntimeError: Captured output (...) does not match sys.stdout (...)
RuntimeError: TeeStream: deadlock observed joining reader threads (...)
AssertionError: (... LoggingIntercept ...)
```

Pyomo's HiGHS interface wraps every solve in `capture_output(..., capture_fd=True)`: it replaces `sys.stdout`/`sys.stderr` and redirects file descriptors 1 and 2 for the whole process, even when solver output is turned off. Those are process-wide, so two solves in two threads of one process overwrite each other's redirection. A test with several threads solving at once reproduced it (it deadlocked).

## Decision

- **Each run is a separate process**, started by the author's request instead of serialising solves with a lock. `run_in_background` starts `run_session` in a daemon `multiprocessing` process and returns it; nothing else in the session design changes (files, statuses, result, rerun).
- **Start method "spawn"**, not "fork": the Streamlit server has threads of its own, which forking would copy in an undefined state.
- **The app script guards its entry point** with `if __name__ == "__main__":`. With "spawn", a child process re-imports the parent's main script; Streamlit runs `app.py` as `__main__`, so without the guard every run re-executed the app, including the start-up step that marks running sessions as interrupted. Children import it as `__mp_main__` and skip it.
- **Daemon processes stop with the app**; `mark_interrupted` flags their sessions on the next start, as before.
- **Cancelling stays cooperative** (the `cancel` marker, checked between windows). A process could be terminated at once, but that would need its PID tracked across app reruns and the status written by the app; left as a possible improvement.

## Alternatives considered

- **Keep threads and serialise solves with a process-wide lock.** Smallest change, but sessions would wait for each other at every window, and any other library writing to standard output during a solve could still interfere.
- **Call `highspy` directly instead of through Pyomo.** Avoids the redirection, but gives up the modelling layer chosen in [ADR 0006](0006-optimisation-modelling-and-solver.md).

## Consequences

- Concurrent runs are isolated: separate memory, separate standard output, true parallelism across CPU cores.
- Starting a run costs about a second for the new interpreter to import the package.
- Everything passed to the process (`SessionStore`, backend) must be picklable; both are plain objects.
- Tests cover several sessions running at once and the app being imported by a spawned process without side effects.
