from dataclasses import replace

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.sources.get_source import GetSourceCommand
from autotrading.application.sources.source_offer import SourceOffer
from autotrading.domain.errors import AutotradingError
from autotrading.domain.sources.source_catalog import SourceCatalog
from tests.fakes.volumes import FakeVolumesAdapter
from tests.support.flow_steps import provider_key_registered, valid_command
from tests.support.flows import scenario_catalog
from tests.support.platform import Platform
from tests.support.source_selections import a_source_request, reader_of
from tests.support.steps import quoted

scenarios("E1-flussi-autonomi/F1.3-fonti-dati/R1.3.1-catalogo-delle-fonti.feature")


@pytest.fixture
def platform() -> Platform:
    platform = Platform()
    platform.model_catalog = scenario_catalog()
    return platform


@pytest.fixture
def consulted() -> dict[str, object]:
    return {}


@when(quoted('"{user}" consulta il catalogo delle fonti'))
def consult_catalog(platform: Platform, user: str, consulted: dict[str, object]) -> None:
    consulted["catalog"] = platform.use_cases_of(user).list_sources.execute()


@when(quoted('"{user}" consulta la fonte "{name}" nel catalogo'))
def consult_source(platform: Platform, user: str, name: str, consulted: dict[str, object]) -> None:
    consulted[name] = platform.use_cases_of(user).get_source.execute(GetSourceCommand(name))


@then("il catalogo contiene le fonti:")
def catalog_contains(consulted: dict[str, object], datatable: list[list[str]]) -> None:
    """Every source of the table with the adapter that offers it; the two sentiments are now the two adapters of the
    source sentiment (R4.1.1, ADR fonti-con-adapter-dichiarati)."""
    catalog = consulted["catalog"]
    assert isinstance(catalog, SourceCatalog)
    offered = [(source.name, adapter.name) for source in catalog.sources for adapter in source.adapters]
    assert offered == [reader_of(row[0].strip()) for row in datatable[1:]]


@then(quoted('la fonte "{name}" ha i parametri:'))
def source_has_parameters(consulted: dict[str, object], name: str, datatable: list[list[str]]) -> None:
    offer = consulted[name]
    assert isinstance(offer, SourceOffer)
    offered = offer.source
    shown = [
        [parameter.label, str(parameter.default), f"da {parameter.minimum} a {parameter.maximum}"]
        for parameter in offered.definition.parameters
    ]
    assert shown == [[cell.strip() for cell in row] for row in datatable[1:]]


@given(quoted('che la piattaforma aggiunge la fonte "{source}" con l\'adapter "{adapter}"'))
def source_added(platform: Platform, source: str, adapter: str) -> None:
    assert source == "volumi"
    platform.source_systems = replace(platform.source_systems, volumes=(FakeVolumesAdapter(adapter),))


@given(quoted('che la piattaforma ritira la fonte "{source}"'))
def source_retired(platform: Platform, source: str) -> None:
    assert source == "sentiment"
    platform.source_systems = replace(platform.source_systems, sentiments=())


def offered_sources(consulted: dict[str, object]) -> list[tuple[str, str]]:
    catalog = consulted["catalog"]
    assert isinstance(catalog, SourceCatalog)
    return [(source.name, adapter.name) for source in catalog.sources for adapter in source.adapters]


@then(quoted('il catalogo contiene la fonte "{source}" con l\'adapter "{adapter}"'))
def catalog_contains_source(consulted: dict[str, object], source: str, adapter: str) -> None:
    assert (source, adapter) in offered_sources(consulted)


@then(quoted('il catalogo non contiene la fonte "{source}"'))
def catalog_without_source(consulted: dict[str, object], source: str) -> None:
    assert source not in {name for name, _ in offered_sources(consulted)}


@then(quoted('"{user}" può creare un flusso con la fonte "{source}"'))
def flow_created_with_source(platform: Platform, consulted: dict[str, object], user: str, source: str) -> None:
    (adapter,) = [adapter for name, adapter in offered_sources(consulted) if name == source]
    provider_key_registered(platform, user, "openrouter")
    command = replace(valid_command(platform, user, "alfa"), sources=(a_source_request(source, None, None, adapter),))
    flow = platform.use_cases_of(user).create_flow.execute(command)
    chosen = [(selection.name, selection.adapters[0].name) for selection in flow.configuration.sources]
    assert chosen == [(source, adapter)]


@then(quoted('la creazione di un flusso di "{user}" con la fonte "{source}" è rifiutata con il motivo "{reason}"'))
def flow_refused_with_source(platform: Platform, user: str, source: str, reason: str) -> None:
    provider_key_registered(platform, user, "openrouter")
    command = replace(valid_command(platform, user, "alfa"), sources=(a_source_request(source),))
    with pytest.raises(AutotradingError) as refusal:
        platform.use_cases_of(user).create_flow.execute(command)
    assert str(refusal.value) == reason
