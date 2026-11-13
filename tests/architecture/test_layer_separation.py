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
    source_modules,
    technology_folders,
    violations_of,
)

PYPROJECT = SOURCE_ROOT.parents[1] / "pyproject.toml"


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
