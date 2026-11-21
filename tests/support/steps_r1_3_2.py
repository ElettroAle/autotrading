import json
from dataclasses import replace

import pytest
from pytest_bdd import given, parsers, then, when

from autotrading.application.flows.get_flow_version import GetFlowVersionCommand
from autotrading.domain.flows.selections import DEFAULT_WEIGHT, ActiveSource
from tests.support.flow_cycles import FlowCycles
from tests.support.flows import scenario_catalog
from tests.support.lifecycle_steps import Lifecycle, add_flow, flow_named, modify
from tests.support.platform import Platform
from tests.support.source_collection import SourceCycle
from tests.support.source_selections import (
    BEFORE_THE_ADAPTERS,
    PLATFORM_CATALOG,
    a_source,
    a_source_request,
    reader_of,
)
from tests.support.steps import quoted


@pytest.fixture
def cycle() -> SourceCycle:
    return SourceCycle()


@pytest.fixture
def flow_cycles() -> FlowCycles:
    """The same flow run as the worker composes its cycle, for what the agent is told beyond the sources."""
    return FlowCycles()


@pytest.fixture
def lifecycle() -> Lifecycle:
    return Lifecycle()


@pytest.fixture
def platform() -> Platform:
    platform = Platform()
    platform.model_catalog = scenario_catalog()
    return platform


def names(text: str) -> list[str]:
    return [name.strip() for name in text.split(",")]


def select(cycle: SourceCycle, flow_cycles: FlowCycles, flow: str, source: str, weight: int = DEFAULT_WEIGHT) -> None:
    cycle.activate(source, weight)
    name, adapter = reader_of(source)
    parameters = PLATFORM_CATALOG.find(name).settings(adapter, {})
    selection = a_source(name, weight, parameters, adapter)
    flow_cycles.reconfigure(
        flow, lambda configuration: replace(configuration, sources=(*configuration.sources, selection))
    )


def weights_in_context(cycle: SourceCycle) -> dict[str, set[int]]:
    """The weights in the context by the names of the specifications: a sentiment by the name it had before the
    adapters (R4.1.1)."""
    document = json.loads(cycle.agent_context().messages()[1].content)
    named = {reader: name for name, reader in BEFORE_THE_ADAPTERS.items()}
    weights: dict[str, set[int]] = {}
    for source in document["fonti"]:
        name = named.get((source["fonte"], source["adapter"]), source["fonte"])
        weights.setdefault(name, set()).add(source["peso"])
    return weights


@given(quoted('che "{user}" ha il flusso "{flow}" con asset "{assets}"'))
def flow_with_assets(cycle: SourceCycle, flow_cycles: FlowCycles, user: str, flow: str, assets: str) -> None:
    cycle.assets = tuple(names(assets))
    flow_cycles.add_flow(user, flow, assets=cycle.assets)


@given(quoted('che il flusso "{flow}" ha attiva la fonte "{source}"'))
@given(quoted('che il flusso "{flow}" ha attiva la fonte "{source}" senza parametri'))
def one_active_source(cycle: SourceCycle, flow_cycles: FlowCycles, flow: str, source: str) -> None:
    select(cycle, flow_cycles, flow, source)


@given(quoted('che il flusso "{flow}" ha attive le fonti "{active}" e non "{inactive}"'))
@given(quoted('che il flusso "{flow}" ha attive le fonti "{active}" senza pesi'))
def active_sources(cycle: SourceCycle, flow_cycles: FlowCycles, flow: str, active: str) -> None:
    for source in names(active):
        select(cycle, flow_cycles, flow, source)


@given(
    parsers.re(
        r'^che il flusso "(?P<flow>[^"]+)" ha attive le fonti "(?P<first>[^"]+)" con peso (?P<first_weight>\d+) '
        r'e "(?P<second>[^"]+)" con peso (?P<second_weight>\d+)$'
    )
)
def weighted_sources(  # noqa: PLR0917 - one argument per value of the step
    cycle: SourceCycle,
    flow_cycles: FlowCycles,
    flow: str,
    first: str,
    first_weight: str,
    second: str,
    second_weight: str,
) -> None:
    select(cycle, flow_cycles, flow, first, int(first_weight))
    select(cycle, flow_cycles, flow, second, int(second_weight))


@given(quoted('che il flusso "{flow}" segue il system prompt predefinito'))
def default_prompt(flow_cycles: FlowCycles, flow: str) -> None:
    assert flow_cycles.flow(flow).configuration.system_prompt is None


@given(quoted('che il flusso "{flow}" ha un system prompt personalizzato "{prompt}"'))
def own_prompt(flow_cycles: FlowCycles, flow: str, prompt: str) -> None:
    flow_cycles.reconfigure(flow, lambda configuration: replace(configuration, system_prompt=prompt))


@when(
    parsers.re(
        r'^"(?P<user>[^"]+)" modifica il flusso "(?P<flow>[^"]+)" con (?P<kind>peso|numero notizie) (?P<value>\d+) '
        r'per la fonte "(?P<source>[^"]+)"$'
    )
)
def modify_source(
    platform: Platform,
    cycle: SourceCycle,
    lifecycle: Lifecycle,
    user: str,
    flow: str,
    *,
    kind: str,
    value: str,
    source: str,
) -> None:
    # The cycle of this feature runs on its own fakes: the flow to modify lives on the platform, with the same assets.
    add_flow(platform, lifecycle, user, flow, assets=cycle.assets)
    request = (
        a_source_request(source, int(value))
        if kind == "peso"
        else a_source_request(source, None, {"numero_notizie": int(value)})
    )
    modify(platform, lifecycle, user, flow, sources=(request,))


@when(quoted('il flusso "{flow}" esegue un ciclo'))
def run_cycle(cycle: SourceCycle, flow_cycles: FlowCycles, flow: str) -> None:
    cycle.run()
    flow_cycles.run(flow)


@then(quoted('la fonte "{source}" è interrogata per "{first}" e per "{second}"'))
def asked_for_every_asset(cycle: SourceCycle, source: str, first: str, second: str) -> None:
    assert [reading.asset for reading in cycle.reader(source).readings] == [first, second]


@then(quoted('la fonte "{source}" non è interrogata'))
def not_asked(cycle: SourceCycle, source: str) -> None:
    assert cycle.reader(source).readings == []


@then("il contesto inviato all'agente non contiene notizie")
def context_without_news(cycle: SourceCycle) -> None:
    weights = weights_in_context(cycle)
    assert weights
    assert "notizie" not in weights


@then(
    parsers.re(
        r"^il contesto comunica all'agente il peso (?P<weight>\d+) "
        r'per "(?P<first>[^"]+)" e per "(?P<second>[^"]+)"$'
    )
)
def same_weight(cycle: SourceCycle, weight: str, first: str, second: str) -> None:
    assert weights_in_context(cycle) == {first: {int(weight)}, second: {int(weight)}}


@then(
    parsers.re(
        r"^il contesto comunica all'agente il peso (?P<first_weight>\d+) "
        r'per "(?P<first>[^"]+)" e (?P<second_weight>\d+) per "(?P<second>[^"]+)"$'
    )
)
def own_weights(cycle: SourceCycle, first: str, first_weight: str, second: str, second_weight: str) -> None:
    assert weights_in_context(cycle) == {first: {int(first_weight)}, second: {int(second_weight)}}


@then(
    parsers.re(
        r'^la fonte "(?P<source>[^"]+)" è interrogata con numero notizie (?P<count>\d+) '
        r"ed età massima (?P<hours>\d+) ore$"
    )
)
def asked_with_defaults(cycle: SourceCycle, source: str, count: str, hours: str) -> None:
    settings = [reading.settings for reading in cycle.reader(source).readings]
    assert settings == [{"numero_notizie": int(count), "eta_massima_ore": int(hours)}]


@then(quoted('la modifica è rifiutata con il motivo "{reason}"'))
def modification_refused(lifecycle: Lifecycle, reason: str) -> None:
    assert str(lifecycle.error) == reason


WEIGHT_RULE = (
    "- quando le fonti sono in disaccordo prevale quella col peso più alto, non il numero dei segnali;",
    "- più valori della stessa fonte (per esempio medie, MACD e RSI degli indicatori) contano come una fonte sola, col"
    " suo peso;",
    "- le istruzioni del flusso prevalgono sui pesi quando li contraddicono;",
    "- nel ragionamento di un'apertura nomina la fonte che ha deciso la direzione quando le fonti erano in disaccordo;",
    # An aggregate of several adapters carries no weight of its own (R5.1.2, ADR fonte-volumi-con-adapter-binance).
    "- una voce senza peso è un aggregato: riassume gli adapter elencati della sua fonte, ciascuno col suo peso;",
)


def weight_meaning(minimum: str, maximum: str, default: str) -> str:
    return (
        f"- il peso di una fonte è un intero da {minimum} a {maximum}, predefinito {default}: l'importanza relativa"
        " che l'utente dà a ogni fonte;"
    )


def weights_line(weights: str) -> str:
    """The weights as the system prompt reports them: every source of the specifications with the adapter that offers
    it, «fonte · adapter» (R4.1.1, ADR fonti-con-adapter-dichiarati)."""
    pairs = (weight.strip().rpartition(" ") for weight in weights.split(","))
    labelled = ", ".join(f"{ActiveSource(*reader_of(name)).label} {value}" for name, _, value in pairs)
    return f"- pesi delle fonti attive del flusso: {labelled};"


@then(
    parsers.re(
        r"^il system prompt inviato all'agente dice che il peso è un intero da (?P<minimum>\d+) a (?P<maximum>\d+), "
        r"predefinito (?P<default>\d+), importanza relativa data dall'utente a ogni fonte$"
    )
)
def weight_explained(flow_cycles: FlowCycles, minimum: str, maximum: str, default: str) -> None:
    assert weight_meaning(minimum, maximum, default) in flow_cycles.system_text()


@then("dice che quando le fonti sono in disaccordo prevale quella col peso più alto, non il numero dei segnali")
def heaviest_source_prevails(flow_cycles: FlowCycles) -> None:
    assert WEIGHT_RULE[0] in flow_cycles.system_text()


@then("dice che più valori della stessa fonte contano come una fonte sola, col suo peso")
def values_of_a_source_count_once(flow_cycles: FlowCycles) -> None:
    assert WEIGHT_RULE[1] in flow_cycles.system_text()


@then("dice che le istruzioni del flusso prevalgono sui pesi")
def instructions_prevail(flow_cycles: FlowCycles) -> None:
    assert WEIGHT_RULE[2] in flow_cycles.system_text()


@then(
    "chiede di nominare nel ragionamento di un'apertura la fonte che ha deciso la direzione quando le fonti erano in "
    "disaccordo"
)
def deciding_source_named(flow_cycles: FlowCycles) -> None:
    assert WEIGHT_RULE[3] in flow_cycles.system_text()


@then(quoted('riporta i pesi "{weights}"'))
def weights_reported(flow_cycles: FlowCycles, weights: str) -> None:
    assert weights_line(weights) in flow_cycles.system_text()


@then(quoted('il system prompt inviato all\'agente contiene la regola del peso e i pesi "{weights}"'))
def rule_in_own_prompt(flow_cycles: FlowCycles, weights: str) -> None:
    assert flow_cycles.system_text() == "\n".join(
        ("Decidi con prudenza. " + weight_meaning("1", "10", "5"), *WEIGHT_RULE, weights_line(weights))
    )


@then(quoted('il flusso "{flow}" ha la versione di configurazione {version} con la fonte "{source}" di peso {weight}'))
def version_with_source(
    platform: Platform, lifecycle: Lifecycle, flow: str, version: str, *, source: str, weight: str
) -> None:
    configuration = flow_named(platform, lifecycle.user, flow).configuration
    chosen = [(selection.name, adapter.weight) for selection in configuration.sources for adapter in selection.adapters]
    assert (configuration.version, chosen) == (int(version), [(source, int(weight))])


@then(quoted('la versione {version} del flusso "{flow}" resta consultabile senza fonti'))
def version_without_sources(platform: Platform, lifecycle: Lifecycle, version: str, flow: str) -> None:
    command = GetFlowVersionCommand(flow_named(platform, lifecycle.user, flow).id, int(version))
    assert platform.use_cases_of(lifecycle.user).get_flow_version.execute(command).sources == ()
