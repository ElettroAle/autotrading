"""A source of the flow with its adapters, checked by the catalog of the platform (R1.3.1, R4.1.1, ADR 0031)."""

from dataclasses import replace

import pytest

from autotrading.application.flows.errors import InvalidFlowSettingError
from autotrading.application.flows.ports import AdapterRequest
from autotrading.application.flows.select_source import SelectSourceUseCase
from autotrading.application.sources.list_sources import ListSourcesUseCase
from autotrading.domain.flows.errors import SourceAdapterRequiredError
from autotrading.domain.flows.selections import AdapterSelection, SourceSelection
from autotrading.domain.sources.source_adapter_declaration import SourceConfigurationField
from tests.fakes.source_credentials import FakeConfiguredSourceAdaptersAdapter
from tests.fakes.sources import FakeSentimentAdapter
from tests.support.source_selections import PLATFORM_CATALOG, platform_sources, platform_systems

NOTHING_CONFIGURED = FakeConfiguredSourceAdaptersAdapter()


def test_every_adapter_chosen_gets_its_weight_and_its_parameters_with_the_defaults() -> None:
    sources = SelectSourceUseCase(platform_sources(), NOTHING_CONFIGURED)
    news = PLATFORM_CATALOG.find("notizie")
    first = news.definition.parameters[0]

    assert sources.execute("notizie", [AdapterRequest("RSS")]) == SourceSelection(
        "notizie", (AdapterSelection("RSS", 5, news.settings("RSS", {})),)
    )
    selected = sources.execute("notizie", [AdapterRequest("RSS", 8, {first.key: first.minimum})])
    assert selected.adapters[0].parameters[first.key] == first.minimum


def test_two_adapters_of_the_same_source_are_one_source_with_both() -> None:
    selected = SelectSourceUseCase(platform_sources(), NOTHING_CONFIGURED).execute(
        "sentiment", [AdapterRequest("alternative.me", 3), AdapterRequest("CoinMarketCap", 7)]
    )

    assert [(adapter.name, adapter.weight) for adapter in selected.adapters] == [
        ("alternative.me", 3),
        ("CoinMarketCap", 7),
    ]


@pytest.mark.parametrize(
    ("source", "adapters", "reason"),
    [
        ("oroscopo", [AdapterRequest("RSS")], "fonte non disponibile: oroscopo"),
        ("notizie", [AdapterRequest("Telegram")], "adapter non disponibile per la fonte notizie: Telegram"),
        ("notizie", [AdapterRequest("RSS", None, {"lingua": 1})], "parametro sconosciuto della fonte notizie: lingua"),
    ],
)
def test_a_source_adapter_or_parameter_the_catalog_refuses_reaches_the_flow_with_the_reason(
    source: str, adapters: list[AdapterRequest], reason: str
) -> None:
    with pytest.raises(InvalidFlowSettingError) as raised:
        SelectSourceUseCase(platform_sources(), NOTHING_CONFIGURED).execute(source, adapters)

    assert str(raised.value) == reason


def test_a_source_without_adapters_is_refused_by_the_flow_with_the_reason() -> None:
    with pytest.raises(SourceAdapterRequiredError, match=r"^scegli almeno un adapter della fonte sentiment$"):
        SelectSourceUseCase(platform_sources(), NOTHING_CONFIGURED).execute("sentiment", [])


def test_a_parameter_out_of_range_reaches_the_flow_with_its_label_and_the_values_admitted() -> None:
    first = PLATFORM_CATALOG.find("notizie").definition.parameters[0]

    with pytest.raises(InvalidFlowSettingError) as raised:
        SelectSourceUseCase(platform_sources(), NOTHING_CONFIGURED).execute(
            "notizie", [AdapterRequest("RSS", None, {first.key: first.maximum + 1})]
        )

    assert str(raised.value) == (
        f"parametro fuori dai valori ammessi: {first.label}, da {first.minimum} a {first.maximum}"
    )


def with_paid_adapter() -> ListSourcesUseCase:
    systems = platform_systems()
    key = SourceConfigurationField("api_key", "chiave API", secret=True)
    paid = FakeSentimentAdapter("Pagato", configuration_fields=(key,))
    return ListSourcesUseCase(replace(systems, sentiments=(*systems.sentiments, paid)))


def test_an_adapter_that_needs_configuration_the_tenant_did_not_give_is_refused_with_the_reason() -> None:
    with pytest.raises(InvalidFlowSettingError) as raised:
        SelectSourceUseCase(with_paid_adapter(), NOTHING_CONFIGURED).execute("sentiment", [AdapterRequest("Pagato")])

    assert str(raised.value) == "configura l'adapter Pagato in Impostazioni \u203a Chiavi"


def test_an_adapter_the_tenant_configured_is_activated() -> None:
    configured = FakeConfiguredSourceAdaptersAdapter(frozenset({"Pagato"}))

    selected = SelectSourceUseCase(with_paid_adapter(), configured).execute("sentiment", [AdapterRequest("Pagato", 4)])

    assert [(adapter.name, adapter.weight) for adapter in selected.adapters] == [("Pagato", 4)]
