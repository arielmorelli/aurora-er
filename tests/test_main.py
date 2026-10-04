import pytest

from aurora_er.__main__ import main


def test_main_runs(capsys: pytest.CaptureFixture[str]) -> None:
    main()
    assert "aurora-er" in capsys.readouterr().out
