import os
from pathlib import Path
from typing import Any

from aurora_er.dto import SolveOptionsDTO
from aurora_er.sessions import (
    SessionState,
    SessionStatus,
    SessionStore,
    run_in_background,
    run_session,
)
from aurora_er.solver import BackendOutcome, HighsBackend
from tests.small_inputs import small_config, write_small_spreadsheets

SESSION = "20261004T090000.000000Z"


def _running_session(tmp_path: Path) -> SessionStore:
    store = SessionStore(tmp_path / "sessions")
    folder = store.folder(SESSION)
    folder.mkdir(parents=True)
    write_small_spreadsheets(folder)
    store.write_config(SESSION, small_config(folder))
    store.write_status(SESSION, SessionStatus(state=SessionState.RUNNING, detail=""))
    return store


class _Broken:
    def solve(self, model: Any, options: SolveOptionsDTO) -> BackendOutcome:
        raise RuntimeError("solver crashed")


def test_writes_result_and_done(tmp_path: Path) -> None:
    store = _running_session(tmp_path)
    run_session(store, SESSION, HighsBackend())
    assert store.read_status(SESSION).state is SessionState.DONE
    assert store.read_result(SESSION).result.all_optimal


def test_records_errors_with_their_description(tmp_path: Path) -> None:
    store = _running_session(tmp_path)
    run_session(store, SESSION, _Broken())
    status = store.read_status(SESSION)
    assert status.state is SessionState.ERROR
    assert status.detail == "RuntimeError: solver crashed"


def test_records_missing_files_as_errors(tmp_path: Path) -> None:
    store = _running_session(tmp_path)
    (store.folder(SESSION) / "prices.xlsx").unlink()
    run_session(store, SESSION, HighsBackend())
    assert store.read_status(SESSION).state is SessionState.ERROR


def test_stops_after_a_window_when_cancelled(tmp_path: Path) -> None:
    store = _running_session(tmp_path)
    store.request_cancel(SESSION)
    run_session(store, SESSION, HighsBackend())
    assert store.read_status(SESSION) == SessionStatus(
        state=SessionState.CANCELLED, detail="Cancelled by the user."
    )
    assert not (store.folder(SESSION) / "result.json").exists()


def test_runs_in_a_separate_process(tmp_path: Path) -> None:
    store = _running_session(tmp_path)
    process = run_in_background(store, SESSION, HighsBackend())
    assert process.daemon
    assert process.pid != os.getpid()
    process.join(timeout=60)
    assert process.exitcode == 0
    assert store.read_status(SESSION).state is SessionState.DONE


def test_several_sessions_run_at_the_same_time(tmp_path: Path) -> None:
    stores = [_running_session(tmp_path / str(index)) for index in range(3)]
    processes = [run_in_background(store, SESSION, HighsBackend()) for store in stores]
    for process in processes:
        process.join(timeout=60)
    assert [store.read_status(SESSION).state for store in stores] == [SessionState.DONE] * 3
