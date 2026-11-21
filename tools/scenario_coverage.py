import json
import sys
from collections import Counter
from typing import Any

from tools.feature_catalog import ExpectedScenario, expected_scenarios, scenario_file
from tools.workspace import workspace_path

# Each system runs its scenarios with one runner: a scenario passed only by the other runner is not covered (ADR
# scenari-per-sistema-sotto-la-user-story).
DASHBOARD = "dashboard"
PYTEST = "pytest-bdd"
PLAYWRIGHT = "Playwright"


def passed_runs(report: list[dict[str, Any]]) -> Counter[tuple[str, str]]:
    return Counter(
        (scenario_file(feature["uri"]), element["name"])
        for feature in report
        for element in feature.get("elements", [])
        if _passed(element)
    )


def uncovered_scenarios(
    expected: list[ExpectedScenario],
    pytest_passed: Counter[tuple[str, str]],
    playwright_passed: Counter[tuple[str, str]],
) -> list[str]:
    uncovered = []
    for scenario in expected:
        runner, passed = (PLAYWRIGHT, playwright_passed) if scenario.system == DASHBOARD else (PYTEST, pytest_passed)
        runs = passed[(scenario.file, scenario.scenario)]
        if runs < scenario.runs:
            uncovered.append(
                f"{scenario.file} / {scenario.scenario}: superato {runs} volte su {scenario.runs} da {runner}"
            )
    return uncovered


def _passed(element: dict[str, Any]) -> bool:
    steps = element.get("steps", [])
    return bool(steps) and all(step["result"]["status"] == "passed" for step in steps)


def _passed_in(report: str) -> Counter[tuple[str, str]]:
    return passed_runs(json.loads(workspace_path(report).read_text(encoding="utf-8")))


def main(arguments: list[str]) -> int:
    specs, pytest_report, playwright_report = arguments
    uncovered = uncovered_scenarios(
        expected_scenarios(workspace_path(specs)), _passed_in(pytest_report), _passed_in(playwright_report)
    )
    for line in uncovered:
        print(f"scenario non eseguito o non superato: {line}", file=sys.stderr)
    return 1 if uncovered else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
