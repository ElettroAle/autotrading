import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from gherkin.errors import ParserError
from gherkin.parser import Parser
from gherkin.token_scanner import TokenScanner

from tools.errors import PipelineError

EXCLUDED_TAGS = frozenset({"@pipeline"})
PATH_SEPARATOR = re.compile(r"[\\/]")


class InvalidFeatureError(PipelineError):
    def __init__(self, path: Path, detail: str) -> None:
        super().__init__(f"{path}: {detail}")
        self.path = path


@dataclass(frozen=True, slots=True)
class ExpectedScenario:
    """A scenario to pass, in the file of its system: «<sistema>/<R-slug>.feature» (ADR
    scenari-per-sistema-sotto-la-user-story)."""

    file: str
    scenario: str
    runs: int

    @property
    def system(self) -> str:
        return self.file.split("/")[0]


def scenario_file(path: str) -> str:
    """The folder of the system and the name of the file: pytest-bdd and Playwright name the same file from different
    roots, and the name of the file is the requirement, so the two parts identify it."""
    return "/".join(PATH_SEPARATOR.split(path)[-2:])


def feature_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.feature"))


def parse_feature(path: Path) -> dict[str, Any]:
    try:
        document = Parser().parse(TokenScanner(path.read_text(encoding="utf-8")))
    except ParserError as error:
        raise InvalidFeatureError(path, str(error)) from error
    return cast(dict[str, Any], document["feature"])


def expected_scenarios(root: Path) -> list[ExpectedScenario]:
    return [
        scenario
        for path in feature_files(root)
        for scenario in _expected_in(scenario_file(path.as_posix()), parse_feature(path))
    ]


def _expected_in(file: str, node: dict[str, Any]) -> Iterator[ExpectedScenario]:
    if _is_excluded(node):
        return
    for child in node["children"]:
        rule = child.get("rule")
        if rule is not None:
            yield from _expected_in(file, rule)
        scenario = child.get("scenario")
        if scenario is None or _is_excluded(scenario):
            continue
        yield ExpectedScenario(file, scenario["name"], _runs(scenario))


def _is_excluded(node: dict[str, Any]) -> bool:
    return any(tag["name"] in EXCLUDED_TAGS for tag in node["tags"])


def _runs(scenario: dict[str, Any]) -> int:
    rows = sum(len(examples["tableBody"]) for examples in scenario["examples"])
    return rows or 1
