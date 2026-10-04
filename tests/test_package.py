import aurora_er


def test_package_exposes_version() -> None:
    assert aurora_er.__version__ == "0.1.0"
