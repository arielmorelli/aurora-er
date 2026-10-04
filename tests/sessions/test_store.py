from datetime import UTC, datetime
from pathlib import Path

import pytest

from aurora_er.sessions import SessionResult, SessionState, SessionStatus, SessionStore
from tests.small_inputs import small_config, write_small_spreadsheets

FIRST = "20261004T090000.000000Z"
SECOND = "20261004T100000.000000Z"
RUNNING = SessionStatus(state=SessionState.RUNNING, detail="")


def _uploads(tmp_path: Path) -> dict[str, Path]:
    uploads = tmp_path / "uploads"
    uploads.mkdir(parents=True)
    write_small_spreadsheets(uploads)
    return {"battery.xlsx": uploads / "battery.xlsx", "prices.xlsx": uploads / "prices.xlsx"}


def _store_with_session(tmp_path: Path, session_id: str = FIRST) -> SessionStore:
    store = SessionStore(tmp_path / "sessions")
    folder = store.create(session_id, _uploads(tmp_path / session_id))
    store.write_config(session_id, small_config(folder))
    store.write_status(session_id, RUNNING)
    return store


def test_create_moves_files_into_the_session(tmp_path: Path) -> None:
    uploads = _uploads(tmp_path)
    folder = SessionStore(tmp_path / "sessions").create(FIRST, uploads)
    assert folder == tmp_path / "sessions" / FIRST
    assert sorted(path.name for path in folder.iterdir()) == ["battery.xlsx", "prices.xlsx"]
    assert not any(path.exists() for path in uploads.values())


def test_create_refuses_an_existing_session(tmp_path: Path) -> None:
    store = _store_with_session(tmp_path)
    with pytest.raises(FileExistsError):
        store.create(FIRST, {})


def test_config_round_trips(tmp_path: Path) -> None:
    store = _store_with_session(tmp_path)
    assert store.read_config(FIRST) == small_config(store.folder(FIRST))


def test_status_round_trips_without_leftover_temporary_file(tmp_path: Path) -> None:
    store = _store_with_session(tmp_path)
    error = SessionStatus(state=SessionState.ERROR, detail="boom")
    store.write_status(FIRST, error)
    assert store.read_status(FIRST) == error
    assert not list(store.folder(FIRST).glob(".*.tmp"))


def test_cancel_request(tmp_path: Path) -> None:
    store = _store_with_session(tmp_path)
    assert not store.cancel_requested(FIRST)
    store.request_cancel(FIRST)
    assert store.cancel_requested(FIRST)


def test_list_is_newest_first_with_status(tmp_path: Path) -> None:
    store = _store_with_session(tmp_path, FIRST)
    folder = store.create(SECOND, _uploads(tmp_path / SECOND))
    store.write_config(SECOND, small_config(folder))
    store.write_status(SECOND, SessionStatus(state=SessionState.DONE, detail=""))
    listed = store.list()
    assert [summary.session_id for summary in listed] == [SECOND, FIRST]
    assert listed[0].created_at == datetime(2026, 10, 4, 10, tzinfo=UTC)
    assert [summary.status.state for summary in listed] == [SessionState.DONE, SessionState.RUNNING]


def test_list_skips_folders_without_status(tmp_path: Path) -> None:
    store = _store_with_session(tmp_path)
    (store.root / SECOND).mkdir()
    assert [summary.session_id for summary in store.list()] == [FIRST]


def test_list_of_missing_root_is_empty(tmp_path: Path) -> None:
    assert SessionStore(tmp_path / "nothing").list() == ()


def test_copy_takes_inputs_and_config_but_not_the_outcome(tmp_path: Path) -> None:
    store = _store_with_session(tmp_path)
    store.request_cancel(FIRST)
    copied = store.copy(FIRST, SECOND)
    assert sorted(path.name for path in copied.iterdir()) == [
        "battery.xlsx",
        "config.yaml",
        "prices.xlsx",
    ]
    assert store.read_config(SECOND).battery_sheet.path == copied / "battery.xlsx"


def test_mark_interrupted_only_touches_running_sessions(tmp_path: Path) -> None:
    store = _store_with_session(tmp_path, FIRST)
    folder = store.create(SECOND, _uploads(tmp_path / SECOND))
    store.write_config(SECOND, small_config(folder))
    store.write_status(SECOND, SessionStatus(state=SessionState.DONE, detail=""))
    assert store.mark_interrupted() == (FIRST,)
    assert store.read_status(FIRST).state is SessionState.INTERRUPTED
    assert store.read_status(SECOND).state is SessionState.DONE


def test_result_round_trips(tmp_path: Path) -> None:
    from aurora_er.app import run
    from aurora_er.solver import HighsBackend

    store = _store_with_session(tmp_path)
    outcome = run(store.read_config(FIRST), HighsBackend(), print)
    result = SessionResult(result=outcome.result, warnings=())
    store.write_result(FIRST, result)
    assert store.read_result(FIRST) == result
