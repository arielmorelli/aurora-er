"""Runs the dispatch model on the provided exercise data.

Usage: `python -m aurora_er.example <inputs folder>`.

The spreadsheets in the inputs folder are read and parsed on every run. Values
they do not contain (the battery's starting state, the horizon and solver
limits) are set here, for this example only. Market 1 labels its 01:00/01:30
rows on March clock-change days as 02:00/02:30; they are loaded by position
and reported in the output.
"""

import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from aurora_er.app import run
from aurora_er.attachments import battery_sheet, market_sheets
from aurora_er.config import RunConfig
from aurora_er.dto import BatteryStateDTO, HorizonDTO, SolveOptionsDTO
from aurora_er.report import format_summary, format_window
from aurora_er.solver import HighsBackend, WindowSize

BATTERY_FILE = "Attachment 1.xlsx"
PRICES_FILE = "Attachment 2.xlsx"
START = datetime(2018, 1, 1, tzinfo=UTC)
END = datetime(2021, 1, 1, tzinfo=UTC)


def example_config(inputs_dir: Path) -> RunConfig:
    """Everything the example run needs besides the spreadsheet contents."""
    return RunConfig(
        battery_sheet=battery_sheet(inputs_dir / BATTERY_FILE),
        battery_state=BatteryStateDTO(
            stored_energy_mwh=0.0, cycles_used=0.0, commissioned_at=START
        ),
        market_sheets=market_sheets(inputs_dir / PRICES_FILE),
        horizon=HorizonDTO(start=START, end=END),
        window_size=WindowSize.MONTH,
        options=SolveOptionsDTO(enforce_cycle_pace=False, time_limit_seconds=120, mip_gap=0.0),
    )


def main(arguments: Sequence[str]) -> int:
    """Run the example on the inputs folder given in `arguments` and print a summary."""
    if len(arguments) != 1:
        print("usage: python -m aurora_er.example <inputs folder>", file=sys.stderr)
        return 2
    outcome = run(
        example_config(Path(arguments[0])),
        HighsBackend(),
        lambda window: print(format_window(window), flush=True),
    )
    print()
    print(format_summary(outcome.result, outcome.loaded_markets))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
