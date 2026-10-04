import logging
import time
from datetime import date, timedelta
from datetime import time as clock
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from aurora_er.sessions import SessionState, SessionStatus, SessionStore
from tests.loading.test_battery import ATTACHMENT_1_ROWS
from tests.small_inputs import small_config, write_small_spreadsheets

APP = str(Path(__file__).parents[2] / "src" / "aurora_er" / "ui" / "app.py")
DONE_ID = "20261004T090000.000000Z"
OTHER_ID = "20261004T100000.000000Z"


def _write_example_inputs(folder: Path) -> None:
    folder.mkdir()
    pd.DataFrame(ATTACHMENT_1_ROWS, columns=["Parameter", "Values", "Units"]).to_excel(
        folder / "Attachment 1.xlsx", sheet_name="Data", index=False
    )
    with pd.ExcelWriter(folder / "Attachment 2.xlsx") as writer:
        pd.DataFrame(
            {
                "Time": pd.date_range("2018-01-01", periods=4, freq="30min"),
                "Market 1 Price [£/MWh]": [10.0, 10.0, 300.0, 300.0],
            }
        ).to_excel(writer, sheet_name="Half-hourly data", index=False)
        pd.DataFrame(
            {
                "Time": pd.date_range("2018-01-01", periods=2, freq="60min"),
                "Market 2 Price [£/MWh]": [50.0, 50.0],
            }
        ).to_excel(writer, sheet_name="Hourly data", index=False)


@pytest.fixture
def folders(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    sessions = tmp_path / "sessions"
    inputs = tmp_path / "inputs"
    _write_example_inputs(inputs)
    monkeypatch.setenv("AURORA_SESSIONS_DIR", str(sessions))
    monkeypatch.setenv("AURORA_INPUTS_DIR", str(inputs))
    return sessions, inputs


def _app() -> AppTest:
    app = AppTest.from_file(APP, default_timeout=30)
    app.run()
    return app


def _button(app: AppTest, label: str) -> None:
    next(button for button in app.button if button.label == label).click().run()


def _messages(app: AppTest) -> str:
    return " ".join(m.value for m in [*app.error, *app.success, *app.info])


def _history(app: AppTest) -> AppTest:
    app.segmented_control(key="page").set_value("History").run()
    return app


def test_switches_between_run_and_history(folders: tuple[Path, Path]) -> None:
    app = _app()
    switcher = app.segmented_control(key="page")
    assert switcher.options == ["Run", "History"]
    assert switcher.value == "Run"
    assert any(button.label == "Run" for button in app.button)
    _history(app)
    assert any(button.label == "Refresh" for button in app.button)
    assert not any(button.label == "Run" for button in app.button)


def test_asks_for_the_folders_when_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AURORA_SESSIONS_DIR", raising=False)
    assert "make run" in _app().error[0].value


def test_run_without_inputs_lists_what_is_missing(folders: tuple[Path, Path]) -> None:
    app = _app()
    _button(app, "Run")
    message = app.error[0].value
    assert "Upload the battery parameters spreadsheet." in message
    assert "Choose a window size." in message


def test_fill_with_example_fills_the_form(folders: tuple[Path, Path]) -> None:
    app = _app()
    _button(app, "Fill with example")
    assert app.session_state["start_date"] == date(2018, 1, 1)
    assert app.session_state["end_date"] == date(2021, 1, 1)
    assert app.session_state["window"] == "month"
    assert "Using Attachment 1.xlsx (example)" in [caption.value for caption in app.caption]


class _Records(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def test_fill_with_example_sets_widgets_without_session_state_warnings(
    folders: tuple[Path, Path],
) -> None:
    records = _Records()
    streamlit_logger = logging.getLogger("streamlit")
    streamlit_logger.addHandler(records)
    try:
        app = _app()
        _button(app, "Fill with example")
        app.run()
    finally:
        streamlit_logger.removeHandler(records)
    assert not [message for message in records.messages if "Session State API" in message]
    assert app.number_input(key="limit").value == 120.0


def test_fill_with_example_lists_the_markets_with_their_steps(folders: tuple[Path, Path]) -> None:
    app = _app()
    _button(app, "Fill with example")
    assert app.selectbox(key="step::Half-hourly data").value == timedelta(minutes=30)
    assert app.selectbox(key="step::Hourly data").value == timedelta(hours=1)


def test_run_asks_for_a_missing_step(folders: tuple[Path, Path]) -> None:
    app = _app()
    _button(app, "Fill with example")
    app.session_state["step::Hourly data"] = None
    app.run()
    _button(app, "Run")
    assert 'Choose the step for sheet "Hourly data".' in app.error[0].value


def test_run_reports_inputs_that_do_not_fit(folders: tuple[Path, Path]) -> None:
    app = _app()
    _button(app, "Fill with example")
    _button(app, "Run")
    assert app.segmented_control(key="page").value == "Run"
    assert "Market 1 does not cover the horizon" in app.error[0].value


def test_run_starts_a_session_that_finishes(folders: tuple[Path, Path]) -> None:
    sessions, _ = folders
    app = _app()
    _button(app, "Fill with example")
    app.date_input(key="end_date").set_value(date(2018, 1, 1))
    app.time_input(key="end_time").set_value(clock(2, 0))
    app.run()
    _button(app, "Run")
    store = SessionStore(sessions)
    (summary,) = store.list()
    assert _wait_until_finished(store, summary.session_id) is SessionState.DONE
    assert app.segmented_control(key="page").value == "History"
    assert app.success[0].value == f"Session {summary.session_id} started."
    assert app.session_state["selected_session"] == summary.session_id


def _wait_until_finished(store: SessionStore, session_id: str) -> SessionState:
    deadline = time.monotonic() + 30
    while store.read_status(session_id).state is SessionState.RUNNING:
        assert time.monotonic() < deadline
        time.sleep(0.2)
    return store.read_status(session_id).state


def _done_session(sessions: Path) -> None:
    from aurora_er.app import run
    from aurora_er.sessions import SessionResult
    from aurora_er.solver import HighsBackend

    store = SessionStore(sessions)
    folder = store.folder(DONE_ID)
    folder.mkdir(parents=True)
    write_small_spreadsheets(folder)
    store.write_config(DONE_ID, small_config(folder))
    outcome = run(store.read_config(DONE_ID), HighsBackend(), print)
    store.write_result(DONE_ID, SessionResult(result=outcome.result, warnings=("Warning: x",)))
    store.write_status(DONE_ID, SessionStatus(state=SessionState.DONE, detail=""))


def test_history_is_empty_without_runs(folders: tuple[Path, Path]) -> None:
    assert "No runs yet" in _messages(_history(_app()))


def test_history_shows_a_done_session_with_its_result(folders: tuple[Path, Path]) -> None:
    sessions, _ = folders
    _done_session(sessions)
    app = _history(_app())
    assert [metric.label for metric in app.metric] == [
        "Market profit",
        "Net profit",
        "Cycles used",
        "Replacements",
    ]
    assert app.warning[0].value == "Warning: x"
    assert any(button.label == "Rerun" for button in app.button)


def test_running_session_can_be_cancelled(folders: tuple[Path, Path]) -> None:
    sessions, _ = folders
    _done_session(sessions)
    store = SessionStore(sessions)
    app = _history(_app())
    store.write_status(DONE_ID, SessionStatus(state=SessionState.RUNNING, detail=""))
    app.run()
    _button(app, "Cancel")
    assert store.cancel_requested(DONE_ID)
    assert "Cancel requested" in _messages(app)


def test_marks_sessions_left_running_as_interrupted(folders: tuple[Path, Path]) -> None:
    sessions, _ = folders
    _done_session(sessions)
    store = SessionStore(sessions)
    store.write_status(DONE_ID, SessionStatus(state=SessionState.RUNNING, detail=""))
    app = _history(_app())
    assert store.read_status(DONE_ID).state is SessionState.INTERRUPTED
    assert "The app stopped while this session was running." in _messages(app)


def test_rerun_starts_a_new_session(folders: tuple[Path, Path]) -> None:
    sessions, _ = folders
    _done_session(sessions)
    app = _history(_app())
    _button(app, "Rerun")
    assert "started" in app.success[0].value
    store = SessionStore(sessions)
    new_session = next(s for s in store.list() if s.session_id != DONE_ID)
    assert _wait_until_finished(store, new_session.session_id) is SessionState.DONE


def test_history_lists_sessions_on_the_left_and_selects_on_click(
    folders: tuple[Path, Path],
) -> None:
    sessions, _ = folders
    _done_session(sessions)
    store = SessionStore(sessions)
    store.copy(DONE_ID, OTHER_ID)
    store.write_status(OTHER_ID, SessionStatus(state=SessionState.ERROR, detail="boom"))
    app = _history(_app())
    listed = [button for button in app.button if button.key and button.key.startswith("session::")]
    assert [button.label for button in listed] == [
        "2026-10-04 10:00:00 · error",
        "2026-10-04 09:00:00 · done",
    ]
    assert "boom" in app.error[0].value
    next(button for button in listed if button.label.endswith("done")).click().run()
    assert len(app.metric) == 4


def test_every_run_field_explains_itself(folders: tuple[Path, Path]) -> None:
    app = _app()
    _button(app, "Fill with example")
    fields = [
        *app.number_input,
        *app.checkbox,
        *app.segmented_control,
        *app.selectbox,
        *app.button,
    ]
    unexplained = [
        getattr(field, "label", "") for field in fields if field.key != "page" and not field.help
    ]
    assert unexplained == []
    labelled = [markdown for markdown in app.markdown if markdown.value.endswith("(UTC)")]
    assert labelled and all(markdown.help for markdown in labelled)


def test_importing_the_app_in_a_spawned_process_leaves_running_sessions_alone(
    folders: tuple[Path, Path],
) -> None:
    import runpy

    sessions, _ = folders
    _done_session(sessions)
    store = SessionStore(sessions)
    store.write_status(DONE_ID, SessionStatus(state=SessionState.RUNNING, detail=""))
    runpy.run_path(APP, run_name="__mp_main__")
    assert store.read_status(DONE_ID).state is SessionState.RUNNING


def test_session_summary_line_shows_dates_windows_and_status(folders: tuple[Path, Path]) -> None:
    sessions, _ = folders
    _done_session(sessions)
    captions = [caption.value for caption in _history(_app()).caption]
    assert "2018-01-01 → 2018-01-01 · month windows · done" in captions
    assert not any(DONE_ID in caption for caption in captions)


def test_warns_that_closing_the_app_stops_running_sessions(folders: tuple[Path, Path]) -> None:
    notice = _app().info[0].value
    assert notice.startswith("This is a prototype")
    assert "stopping the app stops any running sessions" in notice
