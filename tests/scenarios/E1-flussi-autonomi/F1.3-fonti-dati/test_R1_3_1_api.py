import pytest
from pytest_bdd import scenarios, then, when

from autotrading.application.sources.get_source import GetSourceCommand
from autotrading.application.sources.source_offer import SourceOffer
from autotrading.domain.sources.source_catalog import SourceCatalog
from tests.support.platform import Platform
from tests.support.source_selections import reader_of
from tests.support.steps import quoted

scenarios("E1-flussi-autonomi/F1.3-fonti-dati/R1.3.1-catalogo-delle-fonti/api/R1.3.1-catalogo-delle-fonti.feature")


@pytest.fixture
def platform() -> Platform:
    return Platform()


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
