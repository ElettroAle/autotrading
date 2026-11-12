import json

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support.source_collection import SourceCycle
from tests.support.steps import quoted

scenarios("E1-flussi-autonomi/F1.3-fonti-dati/R1.3.2-selezione-pesi-e-parametri-delle-fonti.feature")


@pytest.fixture
def cycle() -> SourceCycle:
    return SourceCycle()


def names(text: str) -> list[str]:
    return [name.strip() for name in text.split(",")]


def weights_in_context(cycle: SourceCycle) -> dict[str, set[int]]:
    document = json.loads(cycle.agent_context().messages()[1].content)
    weights: dict[str, set[int]] = {}
    for source in document["fonti"]:
        weights.setdefault(source["fonte"], set()).add(source["peso"])
    return weights


@given(quoted('che "{user}" ha il flusso "{flow}" con asset "{assets}"'))
def flow_with_assets(cycle: SourceCycle, assets: str) -> None:
    cycle.assets = tuple(names(assets))


@given(quoted('che il flusso "{flow}" ha attiva la fonte "{source}"'))
@given(quoted('che il flusso "{flow}" ha attiva la fonte "{source}" senza parametri'))
def one_active_source(cycle: SourceCycle, source: str) -> None:
    cycle.activate(source)


@given(quoted('che il flusso "{flow}" ha attive le fonti "{active}" e non "{inactive}"'))
@given(quoted('che il flusso "{flow}" ha attive le fonti "{active}" senza pesi'))
def active_sources(cycle: SourceCycle, active: str) -> None:
    for source in names(active):
        cycle.activate(source)


@given(
    parsers.re(
        r'^che il flusso "(?P<flow>[^"]+)" ha attive le fonti "(?P<first>[^"]+)" con peso (?P<first_weight>\d+) '
        r'e "(?P<second>[^"]+)" con peso (?P<second_weight>\d+)$'
    )
)
def weighted_sources(cycle: SourceCycle, first: str, first_weight: str, second: str, second_weight: str) -> None:
    cycle.activate(first, int(first_weight))
    cycle.activate(second, int(second_weight))


@when(quoted('il flusso "{flow}" esegue un ciclo'))
def run_cycle(cycle: SourceCycle) -> None:
    cycle.run()


@then(quoted('la fonte "{source}" è interrogata per "{first}" e per "{second}"'))
def asked_for_every_asset(cycle: SourceCycle, source: str, first: str, second: str) -> None:
    assert [reading.asset for reading in cycle.readers[source].readings] == [first, second]


@then(quoted('la fonte "{source}" non è interrogata'))
def not_asked(cycle: SourceCycle, source: str) -> None:
    assert cycle.readers[source].readings == []


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
    settings = [reading.settings for reading in cycle.readers[source].readings]
    assert settings == [{"numero_notizie": int(count), "eta_massima_ore": int(hours)}]
