"""ADR-fonte-volumi-con-adapter-binance: the volumes source is a per-asset source of the catalog of the domain, offered
by the adapters of VolumesPort and read by one reader for every adapter in the common construction of the readers; the
aggregate weighted on the volumes is a rule of the domain applied when the context of the cycle is composed; the
Binance adapter lives in its own folder, reaches the public market data with httpx alone, carries only raw data,
declares no configuration and no parameter of its own, and is the adapter the bootstrap passes to the sources of the
installation.
"""

import ast
import tomllib
from pathlib import Path

import pytest

from autotrading.adapters.outbound.binance import volumes
from autotrading.domain.sources.source_catalog import SOURCES
from autotrading.domain.sources.volumes import VOLUMES
from tests.support.architecture import SOURCE_ROOT, TECHNOLOGY_LIBRARIES

ROOT = Path(SOURCE_ROOT)
REPOSITORY = ROOT.parents[1]
FOLDER = "adapters/outbound/binance"
PACKAGE = "autotrading.adapters.outbound.binance"
READERS = ROOT / "application" / "sources" / "source_readers.py"
BOOTSTRAP = ROOT / "bootstrap.py"
INDEPENDENT_FOLDERS = "Una cartella di tecnologia non importa un'altra"
VOLUMES_READER = "ReadVolumesUseCase"
COMPOSITION = "binance_adapters"
CONTEXT = "ComposeCycleContextUseCase"
AGGREGATES = "AggregateCycleSourcesUseCase"
RULES_OF_THE_DOMAIN = "autotrading.domain.sources.volume_figures"


def calls_in(source: str, function_name: str | None, called: str) -> bool:
    """Whether a function of the module, or any when none is named, calls the name given."""
    functions = [node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)]
    return any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == called
        for function in functions
        if function_name is None or function.name == function_name
        for node in ast.walk(function)
    )


def composes_the_context_with_the_aggregates(source: str) -> bool:
    """Whether every composition of the context of the cycle receives the aggregates of the sources."""
    contexts = [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == CONTEXT
    ]
    return bool(contexts) and all(
        any(
            isinstance(argument, ast.Call) and isinstance(argument.func, ast.Name) and argument.func.id == AGGREGATES
            for argument in context.args
        )
        for context in contexts
    )


def imports_the_rules_of_the_domain(source: str) -> bool:
    return any(
        isinstance(node, ast.ImportFrom) and node.module == RULES_OF_THE_DOMAIN for node in ast.walk(ast.parse(source))
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
            "    for volumes in systems.volumes:\n"
            "        readers[VOLUMES.name, volumes.declaration().name] = ReadVolumesUseCase(volumes, cycle_minutes)\n"
            "    return readers\n",
            True,
        ),
        ("def readers_of(systems, forecasts, cycle_minutes):\n    return {}\n", False),
    ],
)
def test_adr_fonte_volumi_con_adapter_binance_a_missing_reader_is_found(source: str, registered: bool) -> None:
    assert calls_in(source, "readers_of", VOLUMES_READER) is registered


def test_adr_fonte_volumi_con_adapter_binance_the_volumes_are_a_per_asset_source_with_a_reader_per_adapter() -> None:
    assert VOLUMES in SOURCES
    assert VOLUMES.per_asset
    assert calls_in(READERS.read_text(encoding="utf-8"), "readers_of", VOLUMES_READER)


@pytest.mark.parametrize(
    ("source", "composed"),
    [
        (
            "def source_systems(hyperliquid, forecaster):\n    return SourceSystems(volumes=(binance_adapters(),))\n",
            True,
        ),
        ("def source_systems(hyperliquid, forecaster):\n    return SourceSystems(volumes=())\n", False),
    ],
)
def test_adr_fonte_volumi_con_adapter_binance_an_installation_without_binance_is_found(
    source: str, composed: bool
) -> None:
    assert calls_in(source, "source_systems", COMPOSITION) is composed


def test_adr_fonte_volumi_con_adapter_binance_the_installation_offers_the_binance_adapter() -> None:
    assert calls_in(BOOTSTRAP.read_text(encoding="utf-8"), "source_systems", COMPOSITION)


@pytest.mark.parametrize(
    ("source", "aggregated"),
    [
        (
            "def cycle():\n"
            "    return ComposeCycleContextUseCase(composer, actions, AggregateCycleSourcesUseCase(), clock)\n",
            True,
        ),
        ("def cycle():\n    return ComposeCycleContextUseCase(composer, actions, clock)\n", False),
        ("def cycle():\n    return None\n", False),
    ],
)
def test_adr_fonte_volumi_con_adapter_binance_a_context_without_the_aggregates_is_found(
    source: str, aggregated: bool
) -> None:
    assert composes_the_context_with_the_aggregates(source) is aggregated


def test_adr_fonte_volumi_con_adapter_binance_the_context_of_the_cycle_adds_the_aggregates() -> None:
    assert composes_the_context_with_the_aggregates(BOOTSTRAP.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("source", "computing"),
    [
        ("from autotrading.domain.sources.volume_figures import volume_weighted\n", True),
        ("from autotrading.domain.sources.volume_snapshot import VolumeSnapshot\n", False),
    ],
)
def test_adr_fonte_volumi_con_adapter_binance_an_adapter_that_computes_is_found(source: str, computing: bool) -> None:
    assert imports_the_rules_of_the_domain(source) is computing


def test_adr_fonte_volumi_con_adapter_binance_the_adapter_carries_only_raw_data() -> None:
    assert not any(
        imports_the_rules_of_the_domain(path.read_text(encoding="utf-8")) for path in (ROOT / FOLDER).glob("*.py")
    )


def test_adr_fonte_volumi_con_adapter_binance_the_folder_reaches_binance_with_httpx_alone() -> None:
    assert TECHNOLOGY_LIBRARIES[FOLDER] == frozenset({"httpx"})
    assert PACKAGE in independent_folders()
    assert {path.name for path in (ROOT / FOLDER).glob("*.py")} >= {"configuration.py", "composition.py"}


def test_adr_fonte_volumi_con_adapter_binance_the_adapter_needs_no_configuration_and_offers_history() -> None:
    declaration = volumes.DECLARATION

    assert (declaration.name, declaration.parameters, declaration.configuration_fields) == ("Binance", (), ())
    assert declaration.offers_history
    assert volumes.BINANCE_URL == "https://data-api.binance.vision"


def test_adr_fonte_volumi_con_adapter_binance_the_folder_has_its_rule_and_is_listed_in_the_contract() -> None:
    rule = (REPOSITORY / ".claude" / "rules" / "tech-binance.md").read_text(encoding="utf-8")
    contract = (REPOSITORY / "CLAUDE.md").read_text(encoding="utf-8")

    assert f"src/autotrading/{FOLDER}/**" in rule
    assert "binance/" in contract
    assert "tech-binance.md" in contract
