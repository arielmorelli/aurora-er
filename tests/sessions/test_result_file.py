import json
from pathlib import Path

from aurora_er.app import run
from aurora_er.sessions import SessionResult
from aurora_er.sessions.result_file import result_from_json, result_to_json
from aurora_er.solver import HighsBackend
from tests.small_inputs import write_small_inputs


def _solved(folder: Path) -> SessionResult:
    outcome = run(write_small_inputs(folder), HighsBackend(), print)
    return SessionResult(result=outcome.result, warnings=("Warning: example",))


def test_round_trips_a_solved_result(tmp_path: Path) -> None:
    session_result = _solved(tmp_path)
    assert result_from_json(result_to_json(session_result)) == session_result


def test_is_plain_json_with_iso_datetimes(tmp_path: Path) -> None:
    document = json.loads(result_to_json(_solved(tmp_path)))
    assert document["horizon"]["start"] == "2018-01-01T00:00:00+00:00"
    assert document["windows"][0]["markets"][0]["step_seconds"] == 1800
    assert document["warnings"] == ["Warning: example"]
