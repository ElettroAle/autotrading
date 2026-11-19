"""R4.1.1: every source offered by the adapters that declare themselves, chosen in the flow each with its weight."""

from dataclasses import dataclass, field

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.adapters.outbound.sqlalchemy.flow_repository import configuration_of, document_of
from autotrading.adapters.outbound.sqlalchemy.source_correspondence import migrated_document
from autotrading.application.flows.create_flow import SourceRequest
from autotrading.application.flows.ports import AdapterRequest
from autotrading.domain.sources.sentiment_index import SentimentIndex
from autotrading.domain.sources.source_catalog import SourceCatalog
from tests.support.flow_cycles import FlowCycles, at
from tests.support.lifecycle_steps import Lifecycle, modify
from tests.support.steps import quoted

scenarios("E4-replay-e-analisi/F4.1-fonti-ad-adapter-configurabili/R4.1.1-fonti-con-adapter-dichiarati.feature")

NEWS_COUNT = "numero_notizie"


@dataclass
class Sources:
    """What the scenario asked of the sources: the catalog listed, and the configuration saved before the adapters."""

    catalog: SourceCatalog | None = None
    saved: tuple[int, dict[str, object]] | None = None
    refused_parameter: dict[str, int] = field(default_factory=dict)

    def listed(self) -> SourceCatalog:
        assert self.catalog is not None
        return self.catalog


@pytest.fixture
def flow_cycles() -> FlowCycles:
    return FlowCycles()


@pytest.fixture
def lifecycle() -> Lifecycle:
    return Lifecycle()


@pytest.fixture
def sources() -> Sources:
    return Sources()


@given(quoted('che "{user}" ha il flusso "{flow}"'))
def flow_of_user(flow_cycles: FlowCycles, user: str, flow: str) -> None:
    flow_cycles.add_flow(user, flow)


@when(quoted('"{user}" chiede l\'elenco delle fonti'))
def list_sources(flow_cycles: FlowCycles, sources: Sources, user: str) -> None:
    sources.catalog = flow_cycles.platform.use_cases_of(user).list_sources.execute()


@then(quoted('la fonte "{source}" ha gli adapter "{first}" e "{second}"'))
def adapters_of_source(sources: Sources, source: str, first: str, second: str) -> None:
    assert [adapter.name for adapter in sources.listed().find(source).adapters] == [first, second]


@then("ogni adapter dichiara parametri, configurazione richiesta e disponibilità dello storico")
def every_adapter_declares(sources: Sources) -> None:
    declarations = [
        (
            offered.parameters_of(adapter.name) == offered.definition.parameters + adapter.parameters,
            isinstance(adapter.configuration_fields, tuple),
            isinstance(adapter.offers_history, bool),
        )
        for offered in sources.listed().sources
        for adapter in offered.adapters
    ]
    assert declarations == [(True, True, True)] * 6


@then(quoted('l\'adapter "{adapter}" dichiara "nessuna configurazione necessaria"'))
def adapter_without_configuration(sources: Sources, adapter: str) -> None:
    [declared] = [each for offered in sources.listed().sources for each in offered.adapters if each.name == adapter]
    assert (declared.needs_configuration, declared.configuration_fields) == (False, ())


@when(
    parsers.re(
        r'^"(?P<user>[^"]+)" attiva nel flusso "(?P<flow>[^"]+)" la fonte "(?P<source>[^"]+)" '
        r'con l\'adapter "(?P<first>[^"]+)" peso (?P<first_weight>\d+) '
        r'e l\'adapter "(?P<second>[^"]+)" peso (?P<second_weight>\d+)$'
    )
)
def activate_two_adapters(  # noqa: PLR0917 - one argument per value of the step
    flow_cycles: FlowCycles,
    lifecycle: Lifecycle,
    user: str,
    flow: str,
    source: str,
    first: str,
    first_weight: str,
    second: str,
    second_weight: str,
) -> None:
    flow_cycles.sentiments[first].index = SentimentIndex(29, "Fear", at("06:00"))
    flow_cycles.sentiments[second].index = SentimentIndex(41, "Fear", at("06:00"))
    request = SourceRequest(
        source, (AdapterRequest(first, int(first_weight)), AdapterRequest(second, int(second_weight)))
    )
    modify(flow_cycles.platform, lifecycle, user, flow, sources=(request,))
    assert lifecycle.error is None


@then("il contesto del prossimo ciclo contiene i due indici, ciascuno con il nome del suo adapter e il suo peso")
def two_indices_in_context(flow_cycles: FlowCycles, lifecycle: Lifecycle) -> None:
    [flow] = flow_cycles.platform.flows.flows
    flow_cycles.run(flow.name.value)
    entries = flow_cycles.context()["fonti"]
    assert isinstance(entries, list)
    assert [
        (entry["adapter"], entry["peso"], entry["valori"]["valore"])
        for entry in entries
        if entry["fonte"] == "sentiment"
    ] == [("alternative.me", 3, "29"), ("CoinMarketCap", 7, "41")]
    assert lifecycle.user == "anna"


@when(quoted('"{user}" attiva nel flusso "{flow}" la fonte "{source}" senza scegliere un adapter'))
def activate_without_adapter(flow_cycles: FlowCycles, lifecycle: Lifecycle, user: str, flow: str, source: str) -> None:
    modify(flow_cycles.platform, lifecycle, user, flow, sources=(SourceRequest(source, ()),))


@then(quoted('la configurazione è rifiutata con il motivo "{reason}"'))
def refused_with_reason(lifecycle: Lifecycle, reason: str) -> None:
    assert str(lifecycle.error) == reason


@given(
    parsers.re(
        r'^che il flusso "(?P<flow>[^"]+)" aveva le fonti "(?P<first>[^"]+)" peso (?P<first_weight>\d+) '
        r'e "(?P<second>[^"]+)" peso (?P<second_weight>\d+)$'
    )
)
def sources_before_the_adapters(  # noqa: PLR0917 - one argument per value of the step
    flow_cycles: FlowCycles,
    sources: Sources,
    flow: str,
    first: str,
    first_weight: str,
    second: str,
    second_weight: str,
) -> None:
    configuration = flow_cycles.flow(flow).configuration
    old_sources = [
        {"name": first, "weight": int(first_weight), "parameters": {}},
        {"name": second, "weight": int(second_weight), "parameters": {}},
    ]
    sources.saved = (configuration.version, {**document_of(configuration), "sources": old_sources})


@when("le fonti passano al modello ad adapter")
def sources_pass_to_adapters(flow_cycles: FlowCycles, sources: Sources) -> None:
    assert sources.saved is not None
    version, saved = sources.saved
    migrated = migrated_document(saved)
    assert migrated is not None
    [flow] = flow_cycles.platform.flows.flows
    flow_cycles.reconfigure(flow.name.value, lambda _: configuration_of(version + 1, migrated))


@then(
    parsers.re(
        r'^il flusso "(?P<flow>[^"]+)" ha la fonte "(?P<source>[^"]+)" con l\'adapter "(?P<first>[^"]+)" '
        r'peso (?P<first_weight>\d+) e l\'adapter "(?P<second>[^"]+)" peso (?P<second_weight>\d+)$'
    )
)
def source_with_two_adapters(  # noqa: PLR0917 - one argument per value of the step
    flow_cycles: FlowCycles,
    flow: str,
    source: str,
    first: str,
    first_weight: str,
    second: str,
    second_weight: str,
) -> None:
    configuration = flow_cycles.flow(flow).configuration
    assert [
        (selection.name, adapter.name, adapter.weight)
        for selection in configuration.sources
        for adapter in selection.adapters
    ] == [(source, first, int(first_weight)), (source, second, int(second_weight))]


@then(quoted('la configurazione del flusso "{flow}" ha una nuova versione'))
def new_version(flow_cycles: FlowCycles, sources: Sources, flow: str) -> None:
    assert sources.saved is not None
    version, _ = sources.saved
    assert flow_cycles.flow(flow).configuration.version == version + 1


@when(quoted('"{user}" imposta un parametro dell\'adapter "{adapter}" a un valore non ammesso'))
def parameter_out_of_range(
    flow_cycles: FlowCycles, lifecycle: Lifecycle, sources: Sources, user: str, adapter: str
) -> None:
    [flow] = flow_cycles.platform.flows.flows
    catalog = flow_cycles.platform.use_cases_of(user).list_sources.execute()
    [offered] = [each for each in catalog.sources if adapter in [declared.name for declared in each.adapters]]
    [parameter] = [each for each in offered.parameters_of(adapter) if each.key == NEWS_COUNT]
    sources.refused_parameter = {NEWS_COUNT: parameter.maximum + 1}
    request = SourceRequest(offered.name, (AdapterRequest(adapter, None, sources.refused_parameter),))
    modify(flow_cycles.platform, lifecycle, user, flow.name.value, sources=(request,))


@then("la configurazione è rifiutata con il motivo che nomina il parametro e i valori ammessi")
def refused_naming_parameter(lifecycle: Lifecycle) -> None:
    assert str(lifecycle.error) == "parametro fuori dai valori ammessi: numero notizie, da 1 a 50"
