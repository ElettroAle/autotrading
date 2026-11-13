import tomllib
from pathlib import Path

import pytest

from tests.architecture.known_violations import KNOWN_VIOLATIONS
from tests.support.architecture import (
    ARCHITECTURAL_LIBRARIES,
    SOURCE_ROOT,
    TECHNOLOGY_LIBRARIES,
    TRANSPORT_LIBRARIES,
    Rule,
    Violation,
    folders_without_a_rule,
    indexed_technology_rules,
    paths_of_rule,
    source_modules,
    technology_folders,
    violations_of,
)

PYPROJECT = SOURCE_ROOT.parents[1] / "pyproject.toml"
CONTRACT = SOURCE_ROOT.parents[1] / "CLAUDE.md"
RULES = SOURCE_ROOT.parents[1] / ".claude" / "rules"


@pytest.fixture(scope="module")
def violations() -> list[Violation]:
    return [violation for module in source_modules() for violation in violations_of(module)]


def _independent_modules() -> set[str]:
    contracts = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["tool"]["importlinter"]["contracts"]
    return {module for contract in contracts if contract["type"] == "independence" for module in contract["modules"]}


def _packages_in(folder: Path) -> list[str]:
    return sorted(child.name for child in folder.iterdir() if (child / "__init__.py").is_file())


@pytest.mark.parametrize("rule", list(Rule))
def test_no_violation_outside_the_known_ones(rule: Rule, violations: list[Violation]) -> None:
    known = KNOWN_VIOLATIONS[rule]
    new = [
        violation.describe() for violation in violations if violation.rule is rule and violation.location not in known
    ]

    assert not new, "\n".join(new)


@pytest.mark.parametrize("rule", list(Rule))
def test_every_known_violation_is_still_there(rule: Rule, violations: list[Violation]) -> None:
    present = {violation.location for violation in violations if violation.rule is rule}
    solved = [f"{location} (Bug {bug})" for location, bug in KNOWN_VIOLATIONS[rule].items() if location not in present]

    assert not solved, "togli da tests/architecture/known_violations.py le voci risolte:\n" + "\n".join(solved)


def test_every_rule_declares_its_known_violations() -> None:
    assert set(KNOWN_VIOLATIONS) == set(Rule)


def test_every_known_violation_names_its_bug() -> None:
    without_bug = [location for known in KNOWN_VIOLATIONS.values() for location, bug in known.items() if bug <= 0]

    assert not without_bug


@pytest.mark.parametrize("folder", ["adapters/inbound", "adapters/outbound"])
def test_every_technology_folder_is_in_the_independence_contract(folder: str) -> None:
    expected = {f"autotrading.{folder.replace('/', '.')}.{name}" for name in _packages_in(SOURCE_ROOT / folder)}

    assert expected <= _independent_modules()


@pytest.mark.parametrize("layer", ["domain", "application"])
def test_every_context_but_tenancy_is_in_the_independence_contract(layer: str) -> None:
    contexts = [name for name in _packages_in(SOURCE_ROOT / layer) if name != "tenancy"]
    expected = {f"autotrading.{layer}.{context}" for context in contexts}

    assert expected <= _independent_modules()


def test_every_technology_folder_declares_its_libraries() -> None:
    assert set(technology_folders()) == set(TECHNOLOGY_LIBRARIES)


def test_every_library_belongs_to_one_technology_folder() -> None:
    libraries = [
        library for owned in TECHNOLOGY_LIBRARIES.values() for library in owned if library not in TRANSPORT_LIBRARIES
    ]

    assert len(libraries) == len(set(libraries))


def test_an_architectural_exception_belongs_to_no_technology_folder() -> None:
    owned = {library for libraries in TECHNOLOGY_LIBRARIES.values() for library in libraries}

    assert not owned & set(ARCHITECTURAL_LIBRARIES)


def test_every_module_an_architectural_exception_names_exists() -> None:
    named = {module for modules in ARCHITECTURAL_LIBRARIES.values() for module in modules}

    assert {module for module in named if not (SOURCE_ROOT / module).is_file()} == set()


def test_every_technology_folder_has_its_rule_in_the_index() -> None:
    rules = indexed_technology_rules(CONTRACT.read_text(encoding="utf-8"))
    paths = [path for rule in rules for path in paths_of_rule((RULES / rule).read_text(encoding="utf-8"))]

    uncovered = folders_without_a_rule(technology_folders(), paths)

    assert not uncovered, (
        "ogni cartella di tecnologia ha una rule .claude/rules/tech-*.md che la copre nei suoi paths, elencata "
        "nell'indice delle rule di CLAUDE.md: " + ", ".join(uncovered)
    )


def test_every_rule_in_the_index_exists() -> None:
    rules = indexed_technology_rules(CONTRACT.read_text(encoding="utf-8"))

    assert rules
    assert [rule for rule in rules if not (RULES / rule).is_file()] == []


@pytest.mark.parametrize(
    ("paths", "uncovered"),
    [
        (["src/autotrading/adapters/outbound/telegram/**"], []),
        (["src/autotrading/adapters/outbound/rss/**"], ["adapters/outbound/telegram"]),
        ([], ["adapters/outbound/telegram"]),
    ],
)
def test_a_folder_no_rule_covers_is_found(paths: list[str], uncovered: list[str]) -> None:
    assert folders_without_a_rule(["adapters/outbound/telegram"], paths) == uncovered


def test_the_index_and_the_paths_of_a_rule_are_read() -> None:
    contract = "| Rule | Copre |\n|---|---|\n| `tech-rss.md` | `adapters/outbound/rss/**` |\n| `ci.md` | x |\n"
    rule = '---\npaths:\n  - "src/autotrading/adapters/outbound/rss/**"\n---\n\n# RSS\n- "not/a/path"\n'

    assert indexed_technology_rules(contract) == ["tech-rss.md"]
    assert paths_of_rule(rule) == ["src/autotrading/adapters/outbound/rss/**"]
