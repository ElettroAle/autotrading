import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from tools.workspace import workspace_path

SERVICE_ROOT = "autotrading"
THRESHOLDS = {"domain": 90.0, "application": 90.0, "totale": 80.0, "dashboard": 90.0}
SERVICE_SCOPES = ("domain", "application", "totale")


@dataclass(frozen=True, slots=True)
class Coverage:
    covered: int
    total: int

    @property
    def percent(self) -> float:
        return 100.0 if self.total == 0 else 100.0 * self.covered / self.total

    def __add__(self, other: Coverage) -> Coverage:
        return Coverage(self.covered + other.covered, self.total + other.total)


def coverage_by_scope(report: dict[str, Any]) -> dict[str, Coverage]:
    scopes = {scope: Coverage(0, 0) for scope in SERVICE_SCOPES}
    for path, data in report["files"].items():
        if not _is_service(path):
            continue
        file_coverage = _file_coverage(data["summary"])
        scopes["totale"] += file_coverage
        layer = _layer_of(path)
        if layer in scopes:
            scopes[layer] += file_coverage
    return scopes


def dashboard_coverage(summary: dict[str, Any]) -> Coverage:
    """Lines and branches of the dashboard, from the json-summary report of Vitest (ADR 0116)."""
    total = summary["total"]
    return Coverage(
        total["lines"]["covered"] + total["branches"]["covered"], total["lines"]["total"] + total["branches"]["total"]
    )


def violations(scopes: dict[str, Coverage]) -> list[str]:
    return [
        f"copertura {scope} {scopes[scope].percent:.2f}% sotto la soglia {threshold:g}%"
        for scope, threshold in THRESHOLDS.items()
        if scope in scopes and scopes[scope].percent < threshold
    ]


def _file_coverage(summary: dict[str, int]) -> Coverage:
    covered = summary["covered_lines"] + summary.get("covered_branches", 0)
    total = summary["num_statements"] + summary.get("num_branches", 0)
    return Coverage(covered, total)


# Pipeline tools are measured for SonarCloud, but the thresholds apply to the service only.
def _is_service(path: str) -> bool:
    return SERVICE_ROOT in Path(path.replace("\\", "/")).parts


def _layer_of(path: str) -> str | None:
    parts = Path(path.replace("\\", "/")).parts
    return next((part for part in parts if part in ("domain", "application")), None)


def _read_json(argument: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(workspace_path(argument).read_text(encoding="utf-8")))


def main(arguments: list[str]) -> int:
    scopes = coverage_by_scope(_read_json(arguments[0]))
    if len(arguments) > 1:
        scopes["dashboard"] = dashboard_coverage(_read_json(arguments[1]))
    problems = violations(scopes)
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
