"""Runs a session to completion and records its outcome in the session folder.

Each run gets its own process: Pyomo's HiGHS interface redirects the process-wide
standard output during every solve, so two solves in one process collide.
"""

import multiprocessing
from multiprocessing.process import BaseProcess

from aurora_er.app import run
from aurora_er.dto import DispatchResultDTO
from aurora_er.report import timestamp_warnings
from aurora_er.sessions.result_file import SessionResult
from aurora_er.sessions.status import SessionState, SessionStatus
from aurora_er.sessions.store import SessionStore
from aurora_er.solver import MilpBackend


class RunCancelledError(Exception):
    """Raised between windows when the session's cancellation was requested."""


def run_session(store: SessionStore, session_id: str, backend: MilpBackend) -> None:
    """Solve `session_id` and write its result and final status; never raises."""

    def stop_if_cancelled(_: DispatchResultDTO) -> None:
        if store.cancel_requested(session_id):
            raise RunCancelledError

    try:
        outcome = run(store.read_config(session_id), backend, stop_if_cancelled)
        store.write_result(
            session_id,
            SessionResult(
                result=outcome.result, warnings=timestamp_warnings(outcome.loaded_markets)
            ),
        )
        store.write_status(session_id, SessionStatus(state=SessionState.DONE, detail=""))
    except RunCancelledError:
        store.write_status(
            session_id,
            SessionStatus(state=SessionState.CANCELLED, detail="Cancelled by the user."),
        )
    except Exception as error:
        store.write_status(
            session_id,
            SessionStatus(state=SessionState.ERROR, detail=f"{type(error).__name__}: {error}"),
        )


def run_in_background(store: SessionStore, session_id: str, backend: MilpBackend) -> BaseProcess:
    """Start `run_session` in a separate daemon process and return the process.

    Uses the "spawn" start method: the app has threads of its own, which forking would
    copy in an undefined state. Daemon processes stop with the app, and
    `SessionStore.mark_interrupted` then flags their sessions on the next start.
    """
    process = multiprocessing.get_context("spawn").Process(
        target=run_session, args=(store, session_id, backend), name=session_id, daemon=True
    )
    process.start()
    return process
