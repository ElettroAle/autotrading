"""R5.1.6: a list parameter of a source is saved ordered and without repetitions, and refused, naming the rule, when a
value is out of its range or the values are too many. On the modification of the flow the api makes, with the catalog
of the platform: which source declares the parameter is read from the catalog, never written here (ADR
parametri-delle-fonti-come-liste-libere).
"""

import pytest
from pytest_bdd import parsers, scenarios, then, when

from autotrading.application.flows.create_flow import SourceRequest
from autotrading.application.flows.ports import AdapterRequest
from autotrading.domain.flows.flow import FIRST_VERSION
from autotrading.domain.sources.source_list_parameter import SourceListParameter
from tests.support.flow_cycles import FlowCycles
from tests.support.lifecycle_steps import Lifecycle, modify
from tests.support.steps import quoted

scenarios(
    "E5-evoluzioni/F5.1-nuove-fonti/R5.1.6-parametri-a-lista-per-le-fonti-di-mercato/api/R5.1.6-parametri-a-lista-per-le-fonti-di-mercato.feature"
)

FLOW = "liste"
LIST = r"\[[^\]]*\]"


@pytest.fixture
def flow_cycles() -> FlowCycles:
    return FlowCycles()


@pytest.fixture
def lifecycle() -> Lifecycle:
    return Lifecycle()


def numbers(text: str) -> tuple[int, ...]:
    inside = text.strip().removeprefix("[").removesuffix("]")
    return tuple(int(piece) for piece in inside.split(",") if piece.strip())


def source_of(flow_cycles: FlowCycles, user: str, key: str) -> tuple[str, str]:
    """The source that declares the list parameter, with its adapter."""
    catalog = flow_cycles.platform.use_cases_of(user).list_sources.execute()
    [(source, adapter)] = [
        (offered.name, adapter.name)
        for offered in catalog.sources
        for adapter in offered.adapters
        if any(
            isinstance(each, SourceListParameter) and each.key == key for each in offered.parameters_of(adapter.name)
        )
    ]
    return source, adapter


def save(flow_cycles: FlowCycles, lifecycle: Lifecycle, user: str, key: str, values: tuple[int, ...]) -> None:
    """The modification of the flow as the API makes it: the source of the parameter with the list asked."""
    source, adapter = source_of(flow_cycles, user, key)
    flow_cycles.add_flow(user, FLOW, sources=(source,))
    request = SourceRequest(source, (AdapterRequest(adapter, None, {key: values}),))
    modify(flow_cycles.platform, lifecycle, user, FLOW, sources=(request,))


# When


@when(parsers.re(rf'^"(?P<user>[^"]+)" salva (?P<key>\w+) (?P<values>{LIST})$'))
def saves_list(flow_cycles: FlowCycles, lifecycle: Lifecycle, user: str, key: str, values: str) -> None:
    save(flow_cycles, lifecycle, user, key, numbers(values))


@when(parsers.re(r'^"(?P<user>[^"]+)" salva (?P<key>\w+) con (?P<count>\d+) valori$'))
def saves_many(flow_cycles: FlowCycles, lifecycle: Lifecycle, user: str, key: str, count: str) -> None:
    save(flow_cycles, lifecycle, user, key, tuple(range(1, int(count) + 1)))


# Then


@then(parsers.re(rf"^la configurazione salvata ha (?P<key>\w+) (?P<values>{LIST})$"))
def saved_list(flow_cycles: FlowCycles, lifecycle: Lifecycle, key: str, values: str) -> None:
    assert lifecycle.error is None
    [source] = flow_cycles.flow(FLOW).configuration.sources
    [adapter] = source.adapters
    assert adapter.parameters[key] == numbers(values)


@then(quoted('il salvataggio è rifiutato con motivo "{reason}"'))
def refused(flow_cycles: FlowCycles, lifecycle: Lifecycle, reason: str) -> None:
    assert str(lifecycle.error) == reason
    assert flow_cycles.flow(FLOW).configuration.version == FIRST_VERSION
