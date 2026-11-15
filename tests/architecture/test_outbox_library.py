"""ADR-outbox-delle-integrazioni-esterne-con-procrastinate: procrastinate is a way of using PostgreSQL, so it lives in
the PostgreSQL folder alone, beside the checkpointer of LangGraph, and the core never reaches it.
"""

import ast
import tomllib
from pathlib import Path

import pytest

from tests.support.architecture import (
    SOURCE_ROOT,
    TECHNOLOGY_LIBRARIES,
    Rule,
    SourceModule,
    source_modules,
    violations_of,
)

REPOSITORY = Path(__file__).resolve().parents[2]
LIBRARY = "procrastinate"
LIBRARY_FOLDER = "adapters/outbound/sqlalchemy"
CORE_CONTRACT = "Domain e application non importano tecnologie"


def _imported_libraries(module: SourceModule) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(module.tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module and not node.level:
            imported.add(node.module.split(".")[0])
    return imported


def importers_of(library: str) -> list[str]:
    """Every module of the platform that imports the library, by its path under the package."""
    return sorted(module.path for module in source_modules(SOURCE_ROOT) if library in _imported_libraries(module))


def test_adr_outbox_the_library_belongs_to_the_postgresql_folder_alone() -> None:
    owners = [folder for folder, libraries in TECHNOLOGY_LIBRARIES.items() if LIBRARY in libraries]

    assert owners == [LIBRARY_FOLDER]


def test_adr_outbox_only_the_postgresql_folder_imports_the_library() -> None:
    importers = importers_of(LIBRARY)

    assert importers
    assert all(path.startswith(f"{LIBRARY_FOLDER}/") for path in importers), importers


@pytest.mark.parametrize(
    "path",
    [
        "application/notifications/notify.py",
        "domain/notifications/outbox_message.py",
        "adapters/outbound/telegram/x.py",
    ],
)
def test_adr_outbox_the_library_outside_its_folder_is_a_violation(path: str) -> None:
    rules = {violation.rule for violation in violations_of(SourceModule.parse(path, "import procrastinate\n"))}

    assert Rule.LIBRARIES_IN_THEIR_FOLDER in rules


def test_adr_outbox_the_library_inside_its_folder_breaks_no_rule() -> None:
    module = SourceModule.parse(f"{LIBRARY_FOLDER}/outbox.py", "import procrastinate\n")

    assert [violation for violation in violations_of(module) if violation.rule is Rule.LIBRARIES_IN_THEIR_FOLDER] == []


def test_adr_outbox_the_core_contract_forbids_the_library() -> None:
    configuration = tomllib.loads((REPOSITORY / "pyproject.toml").read_text(encoding="utf-8"))
    [contract] = [
        contract for contract in configuration["tool"]["importlinter"]["contracts"] if contract["name"] == CORE_CONTRACT
    ]

    assert LIBRARY in contract["forbidden_modules"]
