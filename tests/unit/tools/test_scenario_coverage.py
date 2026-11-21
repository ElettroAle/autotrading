import json
from collections import Counter
from pathlib import Path

import pytest

from tools.feature_catalog import ExpectedScenario
from tools.scenario_coverage import main, passed_runs, uncovered_scenarios

STORY = "E9-prova/F9.9-prova/R9.9.9-prova"
FEATURE = "# language: it\nFunzionalità: R9.9.9 Prova\n  Scenario: {name}\n    Quando a\n    Allora b\n"
NONE = Counter[tuple[str, str]]()


def element(name: str, *statuses: str) -> dict[str, object]:
    return {"name": name, "steps": [{"result": {"status": status}} for status in statuses]}


def feature(uri: str, *elements: dict[str, object]) -> dict[str, object]:
    return {"name": "R9.9.9 Prova", "uri": uri, "elements": list(elements)}


def write_feature(specs: Path, system: str, scenario: str) -> None:
    folder = specs / STORY / system
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "R9.9.9-prova.feature").write_text(FEATURE.format(name=scenario), encoding="utf-8")


def write_report(path: Path, *features: dict[str, object]) -> str:
    path.write_text(json.dumps(list(features)), encoding="utf-8")
    return str(path)


def test_passed_runs_count_only_fully_passed_scenarios_by_file() -> None:
    report = [
        feature(
            r"api\R9.9.9-prova.feature",
            element("A", "passed", "passed"),
            element("B", "passed", "failed"),
            element("C"),
            element("A", "passed"),
        )
    ]

    assert passed_runs(report) == Counter({("api/R9.9.9-prova.feature", "A"): 2})


def test_outline_needs_every_row_to_pass() -> None:
    expected = [ExpectedScenario("api/a.feature", "A", 2), ExpectedScenario("api/a.feature", "B", 1)]
    passed = Counter({("api/a.feature", "A"): 1, ("api/a.feature", "B"): 1})

    uncovered = uncovered_scenarios(expected, passed, NONE)

    assert uncovered == ["api/a.feature / A: superato 1 volte su 2 da pytest-bdd"]


def test_a_dashboard_scenario_passed_only_by_pytest_is_not_covered() -> None:
    # ADR scenari-per-sistema-sotto-la-user-story: a scenario counts only from the runner of its system.
    expected = [ExpectedScenario("dashboard/a.feature", "A", 1)]

    uncovered = uncovered_scenarios(expected, Counter({("dashboard/a.feature", "A"): 1}), NONE)

    assert uncovered == ["dashboard/a.feature / A: superato 0 volte su 1 da Playwright"]


def test_a_worker_scenario_passed_only_by_playwright_is_not_covered() -> None:
    expected = [ExpectedScenario("worker/a.feature", "A", 1)]

    uncovered = uncovered_scenarios(expected, NONE, Counter({("worker/a.feature", "A"): 1}))

    assert uncovered == ["worker/a.feature / A: superato 0 volte su 1 da pytest-bdd"]


@pytest.mark.parametrize("system", ["api", "worker", "forecaster"])
def test_the_scenarios_of_every_system_but_the_dashboard_count_from_pytest(system: str) -> None:
    expected = [ExpectedScenario(f"{system}/a.feature", "A", 1)]

    assert uncovered_scenarios(expected, Counter({(f"{system}/a.feature", "A"): 1}), NONE) == []


def test_main_fails_when_a_scenario_did_not_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    specs = tmp_path / "specs"
    write_feature(specs, "api", "A")
    python = write_report(tmp_path / "cucumber.json")
    dashboard = write_report(tmp_path / "dashboard.json")

    assert main([str(specs), python, dashboard]) == 1
    assert "api/R9.9.9-prova.feature / A" in capsys.readouterr().err


def test_main_passes_when_every_scenario_passed_with_the_runner_of_its_system(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    write_feature(specs, "worker", "A")
    write_feature(specs, "dashboard", "B")
    python = write_report(tmp_path / "cucumber.json", feature(r"worker\R9.9.9-prova.feature", element("A", "passed")))
    dashboard = write_report(
        tmp_path / "dashboard.json",
        feature(rf"..\specs\{STORY}\dashboard\R9.9.9-prova.feature", element("B", "passed")),
    )

    assert main([str(specs), python, dashboard]) == 0


def test_main_fails_when_the_runners_exchange_their_reports(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    write_feature(specs, "worker", "A")
    write_feature(specs, "dashboard", "B")
    python = write_report(tmp_path / "cucumber.json", feature("worker/R9.9.9-prova.feature", element("A", "passed")))
    dashboard = write_report(
        tmp_path / "dashboard.json", feature(f"../specs/{STORY}/dashboard/R9.9.9-prova.feature", element("B", "passed"))
    )

    assert main([str(specs), dashboard, python]) == 1
