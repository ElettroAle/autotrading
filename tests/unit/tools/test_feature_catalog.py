from pathlib import Path

import pytest

from tools.feature_catalog import (
    ExpectedScenario,
    InvalidFeatureError,
    expected_scenarios,
    parse_feature,
    scenario_file,
)

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


STORY = "E9-prova/F9.9-prova/R9.9.9-prova"


def write(directory: Path, name: str, text: str) -> Path:
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_expected_scenarios_count_outline_rows_and_skip_pipeline(tmp_path: Path) -> None:
    write(tmp_path, f"{STORY}/api/R9.9.9-prova.feature", FEATURE)

    assert expected_scenarios(tmp_path) == [
        ExpectedScenario("api/R9.9.9-prova.feature", "Semplice", 1),
        ExpectedScenario("api/R9.9.9-prova.feature", "Con esempi", 2),
    ]


def test_the_same_scenario_of_two_systems_is_expected_from_each(tmp_path: Path) -> None:
    # ADR scenari-per-sistema-sotto-la-user-story: the files of a requirement share the name of the feature.
    write(tmp_path, f"{STORY}/dashboard/R9.9.9-prova.feature", FEATURE)
    write(tmp_path, f"{STORY}/worker/R9.9.9-prova.feature", FEATURE)

    expected = expected_scenarios(tmp_path)

    assert [(scenario.system, scenario.scenario) for scenario in expected] == [
        ("dashboard", "Semplice"),
        ("dashboard", "Con esempi"),
        ("worker", "Semplice"),
        ("worker", "Con esempi"),
    ]


@pytest.mark.parametrize(
    "uri",
    [
        "api/R9.9.9-prova.feature",
        r"api\R9.9.9-prova.feature",
        r"..\specs\E9-prova\F9.9-prova\R9.9.9-prova\api\R9.9.9-prova.feature",
        "../specs/E9-prova/F9.9-prova/R9.9.9-prova/api/R9.9.9-prova.feature",
    ],
)
def test_the_file_of_a_scenario_is_its_system_and_its_name_whatever_the_runner(uri: str) -> None:
    assert scenario_file(uri) == "api/R9.9.9-prova.feature"


def test_feature_tagged_pipeline_expects_nothing(tmp_path: Path) -> None:
    write(tmp_path, f"{STORY}/api/R9.9.9-prova.feature", FEATURE.replace("@R9.9.9", "@R9.9.9 @pipeline"))

    assert expected_scenarios(tmp_path) == []


def test_a_tag_other_than_pipeline_excludes_no_scenario(tmp_path: Path) -> None:
    # ADR nessun-test-escluso-o-saltato: @wip no longer leaves a scenario out of the coverage.
    write(tmp_path, f"{STORY}/api/R9.9.9-prova.feature", FEATURE.replace("@R9.9.9", "@R9.9.9 @wip"))

    assert len(expected_scenarios(tmp_path)) == 2


def test_invalid_feature_raises_typed_error_with_path(tmp_path: Path) -> None:
    path = write(tmp_path, "bad.feature", "# language: it\nQuando manca la funzionalità\n")

    with pytest.raises(InvalidFeatureError) as raised:
        parse_feature(path)

    assert raised.value.path == path


def test_the_scenarios_of_a_rule_are_expected(tmp_path: Path) -> None:
    rule = "\n  Regola: una regola\n\n    Scenario: Nella regola\n      Quando succede\n      Allora va\n"
    write(tmp_path, f"{STORY}/api/R9.9.9-prova.feature", FEATURE + rule)

    assert ExpectedScenario("api/R9.9.9-prova.feature", "Nella regola", 1) in expected_scenarios(tmp_path)
