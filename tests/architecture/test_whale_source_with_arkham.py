"""ADR-fonte-whale-con-adapter-arkham: the whale source is a market source of the catalog of the domain, offered by the
adapters of WhaleTransfersPort and read by one reader for every adapter in the common construction of the readers; the
Arkham adapter lives in its own folder, reaches the Intel API with httpx alone, declares a secret key and its own
threshold, and is the adapter the bootstrap passes to the sources of the installation.
"""

import ast
import tomllib
from pathlib import Path

import pytest

from autotrading.adapters.outbound.arkham import whale_transfers
from autotrading.domain.sources.source_catalog import SOURCES
from autotrading.domain.sources.whale import MINIMUM_USD, WHALE
from tests.support.architecture import SOURCE_ROOT, TECHNOLOGY_LIBRARIES

ROOT = Path(SOURCE_ROOT)
REPOSITORY = ROOT.parents[1]
FOLDER = "adapters/outbound/arkham"
PACKAGE = "autotrading.adapters.outbound.arkham"
READERS = ROOT / "application" / "sources" / "source_readers.py"
BOOTSTRAP = ROOT / "bootstrap.py"
INDEPENDENT_FOLDERS = "Una cartella di tecnologia non importa un'altra"
WHALE_READER = "ReadWhaleTransfersUseCase"
COMPOSITION = "arkham_adapters"


def registers_the_reader(source: str) -> bool:
    """Whether the common construction of the readers builds the reader of the large transfers for every adapter."""
    functions = [node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)]
    return any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == WHALE_READER
        for function in functions
        if function.name == "readers_of"
        for node in ast.walk(function)
    )


def composes_the_adapter(source: str) -> bool:
    """Whether the sources of the installation receive the Arkham adapter from its composition."""
    functions = [node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)]
    return any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == COMPOSITION
        for function in functions
        if function.name == "source_systems"
        for node in ast.walk(function)
    )


def independent_folders() -> list[str]:
    document = tomllib.loads((REPOSITORY / "pyproject.toml").read_text(encoding="utf-8"))
    [contract] = [
        contract
        for contract in document["tool"]["importlinter"]["contracts"]
        if contract["name"] == INDEPENDENT_FOLDERS
    ]
    modules: list[str] = contract["modules"]
    return modules


@pytest.mark.parametrize(
    ("source", "registered"),
    [
        (
            "def readers_of(systems, forecasts, cycle_minutes):\n"
            "    readers = {}\n"
            "    for whales in systems.whales:\n"
            "        reader = ReadWhaleTransfersUseCase(whales, cycle_minutes)\n"
            "        readers[WHALE.name, whales.declaration().name] = reader\n"
            "    return readers\n",
            True,
        ),
        ("def readers_of(systems, forecasts, cycle_minutes):\n    return {}\n", False),
    ],
)
def test_adr_fonte_whale_con_adapter_arkham_a_missing_reader_is_found(source: str, registered: bool) -> None:
    assert registers_the_reader(source) is registered


def test_adr_fonte_whale_con_adapter_arkham_the_whale_source_is_a_market_source_with_a_reader_per_adapter() -> None:
    assert WHALE in SOURCES
    assert not WHALE.per_asset
    assert registers_the_reader(READERS.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("source", "composed"),
    [
        ("def source_systems(hyperliquid, forecaster):\n    return SourceSystems(whales=(arkham_adapters(),))\n", True),
        ("def source_systems(hyperliquid, forecaster):\n    return SourceSystems(whales=())\n", False),
    ],
)
def test_adr_fonte_whale_con_adapter_arkham_an_installation_without_arkham_is_found(
    source: str, composed: bool
) -> None:
    assert composes_the_adapter(source) is composed


def test_adr_fonte_whale_con_adapter_arkham_the_installation_offers_the_arkham_adapter() -> None:
    assert composes_the_adapter(BOOTSTRAP.read_text(encoding="utf-8"))


def test_adr_fonte_whale_con_adapter_arkham_the_folder_reaches_arkham_with_httpx_alone() -> None:
    assert TECHNOLOGY_LIBRARIES[FOLDER] == frozenset({"httpx"})
    assert PACKAGE in independent_folders()
    assert {path.name for path in (ROOT / FOLDER).glob("*.py")} >= {"configuration.py", "composition.py"}


def test_adr_fonte_whale_con_adapter_arkham_the_adapter_declares_a_secret_key_and_its_threshold() -> None:
    declaration = whale_transfers.DECLARATION
    [threshold] = declaration.parameters

    assert [(field.label, field.secret) for field in declaration.configuration_fields] == [("chiave API", True)]
    assert (threshold.key, threshold.default, threshold.minimum, threshold.maximum) == (
        MINIMUM_USD,
        1_000_000,
        100_000,
        1_000_000_000,
    )
    assert declaration.offers_history


def test_adr_fonte_whale_con_adapter_arkham_the_folder_has_its_rule_and_is_listed_in_the_contract() -> None:
    rule = (REPOSITORY / ".claude" / "rules" / "tech-arkham.md").read_text(encoding="utf-8")
    contract = (REPOSITORY / "CLAUDE.md").read_text(encoding="utf-8")

    assert f"src/autotrading/{FOLDER}/**" in rule
    assert "arkham/" in contract
    assert "tech-arkham.md" in contract
