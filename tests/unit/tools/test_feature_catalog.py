from pathlib import Path

import pytest

from tools.feature_catalog import ExpectedScenario, InvalidFeatureError, expected_scenarios, parse_feature

FEATURE = """# language: it
@R9.9.9
Funzionalità: R9.9.9 Prova

  Scenario: Semplice
    Quando succede
    Allora va

  @pipeline
  Scenario: Solo pipeline
    Quando succede
    Allora va

  Schema dello scenario: Con esempi
    Quando succede <x>
    Allora va

    Esempi:
      | x |
      | 1 |
      | 2 |
"""


def write(directory: Path, name: str, text: str) -> Path:
    path = directory / name
    path.write_text(text, encoding="utf-8")
    return path


def test_expected_scenarios_count_outline_rows_and_skip_pipeline(tmp_path: Path) -> None:
    write(tmp_path, "a.feature", FEATURE)

    assert expected_scenarios(tmp_path) == [
        ExpectedScenario("R9.9.9 Prova", "Semplice", 1),
        ExpectedScenario("R9.9.9 Prova", "Con esempi", 2),
    ]


def test_feature_tagged_wip_expects_nothing(tmp_path: Path) -> None:
    write(tmp_path, "a.feature", FEATURE.replace("@R9.9.9", "@R9.9.9 @wip"))

    assert expected_scenarios(tmp_path) == []


def test_invalid_feature_raises_typed_error_with_path(tmp_path: Path) -> None:
    path = write(tmp_path, "bad.feature", "# language: it\nQuando manca la funzionalità\n")

    with pytest.raises(InvalidFeatureError) as raised:
        parse_feature(path)

    assert raised.value.path == path
