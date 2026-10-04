from pathlib import Path

import pytest

from aurora_er.app import run
from aurora_er.dto import DispatchResultDTO
from aurora_er.solver import HighsBackend
from tests.small_inputs import write_small_inputs


def test_loads_inputs_and_solves(tmp_path: Path) -> None:
    solved: list[DispatchResultDTO] = []
    outcome = run(write_small_inputs(tmp_path), HighsBackend(), solved.append)
    assert outcome.result.all_optimal
    assert list(outcome.result.windows) == solved
    assert [loaded.market.name for loaded in outcome.loaded_markets] == ["Market 1", "Market 2"]
    assert outcome.result.market_profit_gbp > 0
    assert all(not loaded.misplaced for loaded in outcome.loaded_markets)


def test_uses_the_injected_backend(tmp_path: Path) -> None:
    class Unavailable:
        def solve(self, model: object, options: object) -> object:
            raise RuntimeError("backend called")

    with pytest.raises(RuntimeError, match="backend called"):
        run(
            write_small_inputs(tmp_path),
            Unavailable(),  # type: ignore[arg-type]
            print,
        )
