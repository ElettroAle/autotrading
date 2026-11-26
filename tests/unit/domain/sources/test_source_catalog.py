import pytest

from autotrading.domain.sources.errors import (
    SourceAdapterNotAvailableError,
    SourceAdapterNotFoundError,
    SourceAdapterWithoutConfigurationError,
    SourceListValueOutOfRangeError,
    SourceNotAvailableError,
    SourceParameterOutOfRangeError,
    TrialAssetRequiredError,
)
from autotrading.domain.sources.forecast import FORECAST
from autotrading.domain.sources.indicators import INDICATORS
from autotrading.domain.sources.news import NEWS
from autotrading.domain.sources.pivots import PIVOTS
from autotrading.domain.sources.sentiment import SENTIMENT
from autotrading.domain.sources.social import SOCIAL
from autotrading.domain.sources.source_adapter_declaration import SourceAdapterDeclaration, SourceConfigurationField
from autotrading.domain.sources.source_catalog import SOURCES, OfferedSource, SourceCatalog
from autotrading.domain.sources.source_definition import SourceDefinition
from autotrading.domain.sources.source_list_parameter import SourceListParameter
from autotrading.domain.sources.source_parameter import SourceParameter
from autotrading.domain.sources.volumes import VOLUMES
from autotrading.domain.sources.whale import WHALE

OWN = SourceParameter("profondita", "profondità", 3, 1, 5, description="Che cosa fa. Valori ammessi. Predefinito.")


def definition(name: str) -> SourceDefinition:
    return SourceDefinition(name, f"fonte {name}", per_asset=True, parameters=())


def adapter(name: str, parameters: tuple[SourceParameter, ...] = ()) -> SourceAdapterDeclaration:
    return SourceAdapterDeclaration(name, f"adapter {name}", parameters, (), offers_history=True)


def offered(name: str, *adapters: SourceAdapterDeclaration) -> OfferedSource:
    return OfferedSource(definition(name), adapters or (adapter("primo"),))


def test_the_sources_of_the_platform_are_declared_once_with_a_single_sentiment() -> None:
    assert SOURCES == (INDICATORS, PIVOTS, FORECAST, SENTIMENT, NEWS, WHALE, VOLUMES, SOCIAL)


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


KEY = SourceConfigurationField("api_key", "Chiave API", secret=True)


def configured(name: str) -> SourceAdapterDeclaration:
    return SourceAdapterDeclaration(name, f"adapter {name}", (), (KEY,), offers_history=False)


def test_the_configurable_adapters_are_those_that_need_configuration_each_once_with_the_sources_it_offers() -> None:
    catalog = SourceCatalog(
        [
            offered("sentiment", adapter("libero"), configured("LunarCrush")),
            offered("social", configured("LunarCrush")),
            offered("balene", configured("Arkham")),
        ]
    )

    assert [(each.declaration.name, each.sources) for each in catalog.configurable_adapters()] == [
        ("Arkham", ("balene",)),
        ("LunarCrush", ("sentiment", "social")),
    ]


def test_finds_a_configurable_adapter_by_name() -> None:
    catalog = SourceCatalog([offered("sentiment", configured("LunarCrush"))])

    assert catalog.configurable_adapter("LunarCrush").declaration == configured("LunarCrush")


def test_an_adapter_without_configuration_is_not_configurable() -> None:
    catalog = SourceCatalog([offered("sentiment", adapter("libero"))])

    with pytest.raises(SourceAdapterWithoutConfigurationError) as raised:
        catalog.configurable_adapter("libero")

    assert (str(raised.value), raised.value.status_code) == ("l'adapter libero non richiede configurazione", 422)


def test_an_adapter_offered_by_no_source_is_not_available() -> None:
    with pytest.raises(SourceAdapterNotFoundError) as raised:
        SourceCatalog([offered("sentiment")]).configurable_adapter("oroscopo")

    assert (str(raised.value), raised.value.status_code) == ("adapter della fonte non disponibile: oroscopo", 404)


def test_a_trial_of_a_per_asset_source_reads_the_asset_chosen() -> None:
    assert offered("indicatori").asset_of_trial(" BTC ") == "BTC"


@pytest.mark.parametrize("asset", [None, "", "  "])
def test_a_trial_of_a_per_asset_source_without_an_asset_does_not_start(asset: str | None) -> None:
    with pytest.raises(TrialAssetRequiredError) as raised:
        offered("indicatori").asset_of_trial(asset)

    assert (str(raised.value), raised.value.status_code, raised.value.details) == (
        "scegli l'asset su cui provare la fonte indicatori",
        422,
        {"field": "asset"},
    )


def test_a_trial_of_a_market_source_reads_the_whole_market() -> None:
    market = OfferedSource(
        SourceDefinition("notizie", "fonte notizie", per_asset=False, parameters=()), (adapter("RSS"),)
    )

    assert market.asset_of_trial("BTC") is None


def test_the_settings_of_a_list_parameter_are_saved_ordered_and_without_repetitions() -> None:
    days = SourceListParameter("giorni", "giorni", (1,), 1, 30, description="Che cosa fa. Valori ammessi. Predefinito.")
    source = OfferedSource(SourceDefinition("pivot", "fonte", per_asset=True, parameters=(days,)), (adapter("primo"),))

    assert source.settings("primo", {"giorni": (7, 1, 7)}) == {"giorni": (1, 7)}
    assert source.settings("primo", {}) == {"giorni": (1,)}
    with pytest.raises(SourceListValueOutOfRangeError, match=r"^giorni: ogni valore tra 1 e 30$"):
        source.settings("primo", {"giorni": (31,)})
