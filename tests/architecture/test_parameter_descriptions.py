"""ADR-descrizioni-dei-parametri-di-fonti-e-modelli: every parameter of an adapter of a source, those of its source
included, and every parameter of a model the platform offers has a description that is not blank, the text of its info
button (R5.5.7). The adapters are found by their declarations, so an adapter added later is checked too.
"""

import importlib
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

import pytest

from autotrading.domain.agent.model_parameter import OFFERED_PARAMETERS, OfferedParameter
from autotrading.domain.sources.source_adapter_declaration import SourceAdapterDeclaration
from autotrading.domain.sources.source_catalog import SOURCES
from tests.support.architecture import SOURCE_ROOT

OUTBOUND = SOURCE_ROOT / "adapters" / "outbound"
PACKAGE_ROOT = SOURCE_ROOT.parent


@dataclass(frozen=True)
class Described:
    """Whatever declares a key and its description: a parameter of a source or of a model."""

    key: str
    description: str


def declarations() -> Iterator[SourceAdapterDeclaration]:
    """Every declaration of an adapter of a source, as the modules of the outbound adapters hold it."""
    for path in sorted(OUTBOUND.rglob("*.py")):
        if "SourceAdapterDeclaration(" not in path.read_text(encoding="utf-8"):
            continue
        module = importlib.import_module(".".join(path.relative_to(PACKAGE_ROOT).with_suffix("").parts))
        yield from (value for value in vars(module).values() if isinstance(value, SourceAdapterDeclaration))


def adapter_parameters() -> Iterator[Described]:
    """The parameters of the sources, which hold for each of their adapters, and those of the adapters themselves."""
    for source in SOURCES:
        yield from (Described(each.key, each.description) for each in source.parameters)
    for declaration in declarations():
        yield from (Described(each.key, each.description) for each in declaration.parameters)


def model_parameters(offered: dict[str, OfferedParameter]) -> Iterator[Described]:
    yield from (Described(key, parameter.description) for key, parameter in offered.items())


def undescribed(parameters: Iterable[Described]) -> list[str]:
    return sorted({parameter.key for parameter in parameters if not parameter.description.strip()})


@pytest.mark.parametrize(
    ("parameters", "found"),
    [
        ([Described("rsi_periodi", "Periodi dell'RSI. Da 2 a 10000. Predefinito: 7, 14.")], []),
        ([Described("rsi_periodi", "")], ["rsi_periodi"]),
        ([Described("temperature", "   ")], ["temperature"]),
    ],
)
def test_adr_descrizioni_dei_parametri_a_parameter_without_a_description_is_found(
    parameters: list[Described], found: list[str]
) -> None:
    assert undescribed(parameters) == found


def test_adr_descrizioni_dei_parametri_every_adapter_of_a_source_is_found() -> None:
    names = {declaration.name for declaration in declarations()}

    assert {"Hyperliquid", "Prophet", "alternative.me", "CoinMarketCap", "RSS", "Arkham", "LunarCrush"} <= names


def test_adr_descrizioni_dei_parametri_every_parameter_of_an_adapter_has_a_description() -> None:
    missing = undescribed(adapter_parameters())

    assert not missing, f"Parametri di adapter senza descrizione: {missing}"


def test_adr_descrizioni_dei_parametri_every_parameter_of_a_model_has_a_description() -> None:
    missing = undescribed(model_parameters(OFFERED_PARAMETERS))

    assert not missing, f"Parametri di modello senza descrizione: {missing}"
    assert set(OFFERED_PARAMETERS) == {"temperature", "max_tokens", "reasoning_effort"}
