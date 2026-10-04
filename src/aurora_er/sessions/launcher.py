"""Validates a run before it is saved, and starts sessions."""

from collections.abc import Callable, Mapping
from pathlib import Path

from aurora_er.config import RunConfig
from aurora_er.dto import BatteryDTO, InvalidDTOError
from aurora_er.loading import InputFileError, read_battery_spec, read_market
from aurora_er.sessions.status import SessionState, SessionStatus
from aurora_er.sessions.store import SessionStore
from aurora_er.solver import InvalidSolveInputError
from aurora_er.solver.validation import validate_inputs


def validation_errors(config: RunConfig) -> tuple[str, ...]:
    """Problems that would stop `config` from running; empty when it can run.

    Reads every spreadsheet and checks the inputs together, without solving.
    """
    try:
        battery = BatteryDTO(
            spec=read_battery_spec(config.battery_sheet), state=config.battery_state
        )
        markets = [read_market(sheet).market for sheet in config.market_sheets]
        validate_inputs(battery, config.horizon, markets)
    except (InputFileError, InvalidDTOError, InvalidSolveInputError) as error:
        return (str(error),)
    except (OSError, ValueError) as error:
        return (f"Could not read the spreadsheets: {error}",)
    return ()


def launch(
    store: SessionStore,
    session_id: str,
    files: Mapping[str, Path],
    config_in: Callable[[Path], RunConfig],
    start: Callable[[str], object],
) -> None:
    """Create `session_id` from `files`, store its config, mark it running and start it.

    `config_in` builds the run config for the session folder; `start` launches the
    worker (in production, `run_in_background`, which uses a separate process).
    """
    folder = store.create(session_id, files)
    store.write_config(session_id, config_in(folder))
    store.write_status(session_id, SessionStatus(state=SessionState.RUNNING, detail=""))
    start(session_id)


def rerun(
    store: SessionStore, source_id: str, session_id: str, start: Callable[[str], object]
) -> None:
    """Start `session_id` as a copy of `source_id`'s inputs and config."""
    store.copy(source_id, session_id)
    store.write_status(session_id, SessionStatus(state=SessionState.RUNNING, detail=""))
    start(session_id)
