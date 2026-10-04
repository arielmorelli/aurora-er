"""File-based session storage: one folder per session under a root folder."""

import os
import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from aurora_er.config import RunConfig
from aurora_er.sessions.config_file import config_from_yaml, config_to_yaml
from aurora_er.sessions.ids import created_at
from aurora_er.sessions.result_file import SessionResult, result_from_json, result_to_json
from aurora_er.sessions.status import SessionState, SessionStatus, format_status, parse_status

CONFIG_FILE = "config.yaml"
STATUS_FILE = "status"
RESULT_FILE = "result.json"
CANCEL_FILE = "cancel"
RUN_FILES = frozenset({STATUS_FILE, RESULT_FILE, CANCEL_FILE})


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionSummary:
    """A session as listed in the history."""

    session_id: str
    """Folder name; the UTC creation time."""

    created_at: datetime
    """When the session was created, in UTC."""

    status: SessionStatus
    """Content of its `status` file."""


class SessionStore:
    """Reads and writes sessions under `root`."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def folder(self, session_id: str) -> Path:
        """The folder of `session_id`."""
        return self.root / session_id

    def create(self, session_id: str, files: Mapping[str, Path]) -> Path:
        """Create the session folder and move `files` into it, renamed to their keys."""
        folder = self.folder(session_id)
        folder.mkdir(parents=True, exist_ok=False)
        for name, source in files.items():
            shutil.move(source, folder / name)
        return folder

    def copy(self, source_id: str, session_id: str) -> Path:
        """Create `session_id` with the inputs and config of `source_id`, without its outcome."""
        folder = self.folder(session_id)
        folder.mkdir(parents=True, exist_ok=False)
        for entry in self.folder(source_id).iterdir():
            if entry.is_file() and entry.name not in RUN_FILES:
                shutil.copy2(entry, folder / entry.name)
        return folder

    def write_config(self, session_id: str, config: RunConfig) -> None:
        """Store `config`; its spreadsheet paths must be inside the session folder."""
        folder = self.folder(session_id)
        _write_atomically(folder / CONFIG_FILE, config_to_yaml(config, folder))

    def read_config(self, session_id: str) -> RunConfig:
        """The run configuration of `session_id`."""
        folder = self.folder(session_id)
        return config_from_yaml((folder / CONFIG_FILE).read_text(encoding="utf-8"), folder)

    def write_status(self, session_id: str, status: SessionStatus) -> None:
        """Replace the status file in one step, so readers never see it half written."""
        _write_atomically(self.folder(session_id) / STATUS_FILE, format_status(status))

    def read_status(self, session_id: str) -> SessionStatus:
        """The status of `session_id`."""
        return parse_status((self.folder(session_id) / STATUS_FILE).read_text(encoding="utf-8"))

    def write_result(self, session_id: str, result: SessionResult) -> None:
        """Store the result of a finished session."""
        _write_atomically(self.folder(session_id) / RESULT_FILE, result_to_json(result))

    def read_result(self, session_id: str) -> SessionResult:
        """The result of a finished session."""
        return result_from_json((self.folder(session_id) / RESULT_FILE).read_text(encoding="utf-8"))

    def request_cancel(self, session_id: str) -> None:
        """Ask the worker running `session_id` to stop after its current window."""
        (self.folder(session_id) / CANCEL_FILE).touch()

    def cancel_requested(self, session_id: str) -> bool:
        """Whether cancelling `session_id` was requested."""
        return (self.folder(session_id) / CANCEL_FILE).exists()

    def list(self) -> tuple[SessionSummary, ...]:
        """Every session with a status file, newest first."""
        if not self.root.exists():
            return ()
        summaries = [
            SessionSummary(
                session_id=folder.name,
                created_at=created_at(folder.name),
                status=self.read_status(folder.name),
            )
            for folder in self.root.iterdir()
            if (folder / STATUS_FILE).is_file()
        ]
        return tuple(sorted(summaries, key=lambda summary: summary.created_at, reverse=True))

    def mark_interrupted(self) -> tuple[str, ...]:
        """Mark every running session as interrupted; for use when the app starts."""
        interrupted = tuple(
            summary.session_id
            for summary in self.list()
            if summary.status.state is SessionState.RUNNING
        )
        for session_id in interrupted:
            self.write_status(
                session_id,
                SessionStatus(
                    state=SessionState.INTERRUPTED,
                    detail="The app stopped while this session was running.",
                ),
            )
        return interrupted


def _write_atomically(path: Path, text: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)
