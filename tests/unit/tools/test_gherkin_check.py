from pathlib import Path

import pytest

from tools.gherkin_check import invalid_features, main

VALID = "# language: it\nFunzionalità: X\n  Scenario: S\n    Quando a\n    Allora b\n"
INVALID = "# language: it\nQuando manca la funzionalità\n"


def test_valid_corpus_has_no_problems(tmp_path: Path) -> None:
    (tmp_path / "ok.feature").write_text(VALID, encoding="utf-8")

    assert invalid_features(tmp_path) == []
    assert main([str(tmp_path)]) == 0


def test_invalid_file_is_reported_by_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "ok.feature").write_text(VALID, encoding="utf-8")
    (tmp_path / "ko.feature").write_text(INVALID, encoding="utf-8")

    assert main([str(tmp_path)]) == 1
    assert "ko.feature" in capsys.readouterr().err
