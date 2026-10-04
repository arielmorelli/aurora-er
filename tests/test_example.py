import dataclasses
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aurora_er.app import run
from aurora_er.dto import DispatchResultDTO, HorizonDTO
from aurora_er.example import example_config, main
from aurora_er.solver import HighsBackend, WindowSize

INPUTS = Path(__file__).parents[1] / "inputs"
START = datetime(2018, 1, 1, tzinfo=UTC)


def test_points_at_the_provided_spreadsheets() -> None:
    config = example_config(INPUTS)
    assert config.battery_sheet.path.exists()
    assert all(sheet.path.exists() for sheet in config.market_sheets)
    assert [sheet.sheet for sheet in config.market_sheets] == ["Half-hourly data", "Hourly data"]


def test_covers_all_provided_data_in_monthly_windows() -> None:
    config = example_config(INPUTS)
    assert config.horizon == HorizonDTO(start=START, end=datetime(2021, 1, 1, tzinfo=UTC))
    assert config.window_size is WindowSize.MONTH


def test_starts_with_a_new_empty_battery() -> None:
    state = example_config(INPUTS).battery_state
    assert (state.stored_energy_mwh, state.cycles_used, state.commissioned_at) == (0, 0, START)


def test_runs_on_the_provided_data() -> None:
    first_day = dataclasses.replace(
        example_config(INPUTS), horizon=HorizonDTO(start=START, end=START + timedelta(days=1))
    )
    solved: list[DispatchResultDTO] = []
    outcome = run(first_day, HighsBackend(), solved.append)
    assert outcome.result.all_optimal
    assert len(solved) == 1
    assert [len(market.charge_mw) for market in outcome.result.windows[0].markets] == [48, 24]
    assert sum(len(loaded.misplaced) for loaded in outcome.loaded_markets) == 6


def test_requires_the_inputs_folder(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 2
    assert "usage" in capsys.readouterr().err
