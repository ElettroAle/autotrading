from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def run_inside_the_test_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Pipeline tools only accept paths inside the working directory, as on the CI runner.
    monkeypatch.chdir(tmp_path)
