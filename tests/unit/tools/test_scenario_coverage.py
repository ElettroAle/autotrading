import json
from collections import Counter
from pathlib import Path

import pytest

from tools.feature_catalog import ExpectedScenario
from tools.scenario_coverage import main, passed_runs, uncovered_scenarios


def element(name: str, *statuses: str) -> dict[str, object]:
    return {"name": name, "steps": [{"result": {"status": status}} for status in statuses]}


def test_passed_runs_count_only_fully_passed_scenarios() -> None:
    report = [
        {
            "name": "F",
            "elements": [
                element("A", "passed", "passed"),
                element("B", "passed", "failed"),
                element("C"),
                element("A", "passed"),
            ],
        }
    ]

    assert passed_runs(report) == Counter({("F", "A"): 2})


def test_outline_needs_every_row_to_pass() -> None:
    expected = [ExpectedScenario("F", "A", 2), ExpectedScenario("F", "B", 1)]

    uncovered = uncovered_scenarios(expected, Counter({("F", "A"): 1, ("F", "B"): 1}))

    assert uncovered == ["F / A: superato 1 volte su 2"]


def test_main_fails_when_a_scenario_did_not_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "a.feature").write_text(
        "# language: it\nFunzionalità: F\n  Scenario: A\n    Quando a\n    Allora b\n", encoding="utf-8"
    )
    report = tmp_path / "cucumber.json"
    report.write_text(json.dumps([]), encoding="utf-8")

    assert main([str(specs), str(report)]) == 1
    assert "F / A" in capsys.readouterr().err


def test_main_passes_when_every_scenario_passed(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "a.feature").write_text(
        "# language: it\nFunzionalità: F\n  Scenario: A\n    Quando a\n    Allora b\n", encoding="utf-8"
    )
    report = tmp_path / "cucumber.json"
    report.write_text(json.dumps([{"name": "F", "elements": [element("A", "passed")]}]), encoding="utf-8")

    assert main([str(specs), str(report)]) == 0


def test_main_counts_the_scenarios_of_every_report(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "a.feature").write_text(
        "# language: it\nFunzionalità: F\n  Scenario: A\n    Quando a\n    Allora b\n", encoding="utf-8"
    )
    (specs / "b.feature").write_text(
        "# language: it\nFunzionalità: G\n  Scenario: B\n    Quando a\n    Allora b\n", encoding="utf-8"
    )
    python = tmp_path / "cucumber.json"
    python.write_text(json.dumps([{"name": "F", "elements": [element("A", "passed")]}]), encoding="utf-8")
    dashboard = tmp_path / "dashboard.json"
    dashboard.write_text(json.dumps([{"name": "G", "elements": [element("B", "passed")]}]), encoding="utf-8")

    assert main([str(specs), str(python), str(dashboard)]) == 0
    assert main([str(specs), str(python)]) == 1
