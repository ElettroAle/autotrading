import json
import sys
from collections import Counter
from typing import Any

from tools.feature_catalog import ExpectedScenario, expected_scenarios
from tools.workspace import workspace_path


def passed_runs(report: list[dict[str, Any]]) -> Counter[tuple[str, str]]:
    return Counter(
        (feature["name"], element["name"])
        for feature in report
        for element in feature.get("elements", [])
        if _passed(element)
    )


def uncovered_scenarios(expected: list[ExpectedScenario], passed: Counter[tuple[str, str]]) -> list[str]:
    return [
        f"{scenario.feature} / {scenario.scenario}: superato {passed[(scenario.feature, scenario.scenario)]}"
        f" volte su {scenario.runs}"
        for scenario in expected
        if passed[(scenario.feature, scenario.scenario)] < scenario.runs
    ]


def _passed(element: dict[str, Any]) -> bool:
    steps = element.get("steps", [])
    return bool(steps) and all(step["result"]["status"] == "passed" for step in steps)


def main(arguments: list[str]) -> int:
    specs, report = workspace_path(arguments[0]), workspace_path(arguments[1])
    passed = passed_runs(json.loads(report.read_text(encoding="utf-8")))
    uncovered = uncovered_scenarios(expected_scenarios(specs), passed)
    for line in uncovered:
        print(f"scenario non eseguito o non superato: {line}", file=sys.stderr)
    return 1 if uncovered else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
