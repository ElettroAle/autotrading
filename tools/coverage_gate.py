import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

THRESHOLDS = {"domain": 90.0, "application": 90.0, "totale": 80.0}


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
    scopes = {scope: Coverage(0, 0) for scope in THRESHOLDS}
    for path, data in report["files"].items():
        file_coverage = _file_coverage(data["summary"])
        scopes["totale"] += file_coverage
        layer = _layer_of(path)
        if layer in scopes:
            scopes[layer] += file_coverage
    return scopes


def violations(scopes: dict[str, Coverage]) -> list[str]:
    return [
        f"copertura {scope} {scopes[scope].percent:.2f}% sotto la soglia {threshold:g}%"
        for scope, threshold in THRESHOLDS.items()
        if scopes[scope].percent < threshold
    ]


def _file_coverage(summary: dict[str, int]) -> Coverage:
    covered = summary["covered_lines"] + summary.get("covered_branches", 0)
    total = summary["num_statements"] + summary.get("num_branches", 0)
    return Coverage(covered, total)


def _layer_of(path: str) -> str | None:
    parts = Path(path.replace("\\", "/")).parts
    return next((part for part in parts if part in ("domain", "application")), None)


def main(arguments: list[str]) -> int:
    report = json.loads(Path(arguments[0]).read_text(encoding="utf-8"))
    problems = violations(coverage_by_scope(report))
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
