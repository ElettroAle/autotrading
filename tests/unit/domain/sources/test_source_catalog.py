import pytest

from autotrading.domain.sources.errors import (
    SourceAdapterNotAvailableError,
    SourceNotAvailableError,
    SourceParameterOutOfRangeError,
)
from autotrading.domain.sources.forecast import FORECAST
from autotrading.domain.sources.indicators import INDICATORS
from autotrading.domain.sources.news import NEWS
from autotrading.domain.sources.pivots import PIVOTS
from autotrading.domain.sources.sentiment import SENTIMENT
from autotrading.domain.sources.source_adapter_declaration import SourceAdapterDeclaration
from autotrading.domain.sources.source_catalog import SOURCES, OfferedSource, SourceCatalog
from autotrading.domain.sources.source_definition import SourceDefinition
from autotrading.domain.sources.source_parameter import SourceParameter

OWN = SourceParameter("profondita", "profondità", 3, 1, 5)


def definition(name: str) -> SourceDefinition:
    return SourceDefinition(name, f"fonte {name}", per_asset=True, parameters=())


def adapter(name: str, parameters: tuple[SourceParameter, ...] = ()) -> SourceAdapterDeclaration:
    return SourceAdapterDeclaration(name, f"adapter {name}", parameters, (), offers_history=True)


def offered(name: str, *adapters: SourceAdapterDeclaration) -> OfferedSource:
    return OfferedSource(definition(name), adapters or (adapter("primo"),))


def test_the_sources_of_the_platform_are_declared_once_with_a_single_sentiment() -> None:
    assert SOURCES == (INDICATORS, PIVOTS, FORECAST, SENTIMENT, NEWS)


def test_lists_the_sources_in_the_order_they_were_declared() -> None:
    catalog = SourceCatalog([offered("pivot"), offered("indicatori")])

    assert [source.name for source in catalog.sources] == ["pivot", "indicatori"]


def test_finds_a_source_by_name() -> None:
    assert SourceCatalog([offered("pivot")]).find("pivot") == offered("pivot")


def test_a_source_not_in_the_catalog_is_not_available() -> None:
    with pytest.raises(SourceNotAvailableError) as raised:
        SourceCatalog([offered("pivot")]).find("oroscopo")

    assert (str(raised.value), raised.value.name, raised.value.status_code) == (
        "fonte non disponibile: oroscopo",
        "oroscopo",
        404,
    )


def test_an_offered_source_finds_its_adapter_by_name() -> None:
    assert offered("sentiment", adapter("uno"), adapter("due")).adapter("due") == adapter("due")


def test_an_adapter_the_source_does_not_offer_is_not_available() -> None:
    with pytest.raises(SourceAdapterNotAvailableError) as raised:
        offered("sentiment", adapter("uno")).adapter("tre")

    assert (str(raised.value), raised.value.source, raised.value.adapter, raised.value.status_code) == (
        "adapter non disponibile per la fonte sentiment: tre",
        "sentiment",
        "tre",
        404,
    )


def test_the_parameters_of_an_adapter_are_those_of_the_source_and_its_own() -> None:
    source = OfferedSource(NEWS, (adapter("lettore", (OWN,)),))

    assert source.parameters_of("lettore") == (*NEWS.parameters, OWN)


def test_the_settings_of_an_adapter_check_its_own_parameters_too() -> None:
    source = OfferedSource(NEWS, (adapter("lettore", (OWN,)),))

    assert source.settings("lettore", {"profondita": 5}) == {
        "numero_notizie": 10,
        "eta_massima_ore": 24,
        "profondita": 5,
    }
    with pytest.raises(SourceParameterOutOfRangeError, match=r"^parametro fuori dai valori ammessi: profondità"):
        source.settings("lettore", {"profondita": 6})


def test_the_name_and_the_description_are_those_of_the_source() -> None:
    source = OfferedSource(NEWS, (adapter("lettore"),))

    assert (source.name, source.description, source.per_asset) == (NEWS.name, NEWS.description, False)
