import dataclasses
from datetime import timedelta
from pathlib import Path

from aurora_er.sessions import SessionState, SessionStore, launch, rerun, validation_errors
from tests.small_inputs import small_config, write_small_spreadsheets

SESSION = "20261004T090000.000000Z"
RERUN = "20261004T100000.000000Z"


def _uploads(tmp_path: Path) -> Path:
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    write_small_spreadsheets(uploads)
    return uploads


def test_valid_inputs_have_no_errors(tmp_path: Path) -> None:
    assert validation_errors(small_config(_uploads(tmp_path))) == ()


def test_reports_horizon_outside_the_prices(tmp_path: Path) -> None:
    config = small_config(_uploads(tmp_path))
    too_long = dataclasses.replace(
        config,
        horizon=dataclasses.replace(config.horizon, end=config.horizon.end + timedelta(hours=1)),
    )
    assert validation_errors(too_long) == ("Market 1 does not cover the horizon",)


def test_reports_unreadable_spreadsheet(tmp_path: Path) -> None:
    uploads = _uploads(tmp_path)
    (uploads / "battery.xlsx").write_text("not a spreadsheet", encoding="utf-8")
    errors = validation_errors(small_config(uploads))
    assert len(errors) == 1
    assert errors[0].startswith("Could not read the spreadsheets")


def test_reports_missing_file(tmp_path: Path) -> None:
    errors = validation_errors(small_config(tmp_path / "empty"))
    assert errors and errors[0].startswith("Could not read the spreadsheets")


def test_launch_creates_running_session_and_starts_it(tmp_path: Path) -> None:
    uploads = _uploads(tmp_path)
    store = SessionStore(tmp_path / "sessions")
    started: list[str] = []
    launch(
        store,
        SESSION,
        {"battery.xlsx": uploads / "battery.xlsx", "prices.xlsx": uploads / "prices.xlsx"},
        small_config,
        started.append,
    )
    assert started == [SESSION]
    assert store.read_status(SESSION).state is SessionState.RUNNING
    assert store.read_config(SESSION) == small_config(store.folder(SESSION))


def test_rerun_starts_a_copy(tmp_path: Path) -> None:
    uploads = _uploads(tmp_path)
    store = SessionStore(tmp_path / "sessions")
    files = {"battery.xlsx": uploads / "battery.xlsx", "prices.xlsx": uploads / "prices.xlsx"}
    launch(store, SESSION, files, small_config, lambda _: None)
    started: list[str] = []
    rerun(store, SESSION, RERUN, started.append)
    assert started == [RERUN]
    assert store.read_status(RERUN).state is SessionState.RUNNING
    assert store.read_config(RERUN) == small_config(store.folder(RERUN))
