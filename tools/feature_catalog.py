from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from gherkin.errors import ParserError
from gherkin.parser import Parser
from gherkin.token_scanner import TokenScanner

from tools.errors import PipelineError

EXCLUDED_TAGS = frozenset({"@wip", "@pipeline"})


class InvalidFeatureError(PipelineError):
    def __init__(self, path: Path, detail: str) -> None:
        super().__init__(f"{path}: {detail}")
        self.path = path


@dataclass(frozen=True, slots=True)
class ExpectedScenario:
    feature: str
    scenario: str
    runs: int


def feature_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.feature"))


def parse_feature(path: Path) -> dict[str, Any]:
    try:
        document = Parser().parse(TokenScanner(path.read_text(encoding="utf-8")))
    except ParserError as error:
        raise InvalidFeatureError(path, str(error)) from error
    return cast(dict[str, Any], document["feature"])


def expected_scenarios(root: Path) -> list[ExpectedScenario]:
    return [scenario for path in feature_files(root) for scenario in _expected_in(parse_feature(path))]


def _expected_in(feature: dict[str, Any]) -> Iterator[ExpectedScenario]:
    if _is_excluded(feature):
        return
    for child in feature["children"]:
        scenario = child.get("scenario")
        if scenario is None or _is_excluded(scenario):
            continue
        yield ExpectedScenario(feature["name"], scenario["name"], _runs(scenario))


def _is_excluded(node: dict[str, Any]) -> bool:
    return any(tag["name"] in EXCLUDED_TAGS for tag in node["tags"])


def _runs(scenario: dict[str, Any]) -> int:
    rows = sum(len(examples["tableBody"]) for examples in scenario["examples"])
    return rows or 1
