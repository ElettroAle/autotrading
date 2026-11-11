import pytest
from pytest_bdd import scenarios, then, when

from autotrading.application.sources.get_source import GetSourceCommand
from autotrading.domain.sources.source_definition import SourceDefinition
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios("E1-flussi-autonomi/F1.3-fonti-dati/R1.3.1-catalogo-delle-fonti.feature")


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
    catalog = consulted["catalog"]
    assert isinstance(catalog, list)
    assert [definition.name for definition in catalog] == [row[0] for row in datatable[1:]]


@then(quoted('la fonte "{name}" ha i parametri:'))
def source_has_parameters(consulted: dict[str, object], name: str, datatable: list[list[str]]) -> None:
    definition = consulted[name]
    assert isinstance(definition, SourceDefinition)
    shown = [
        [parameter.label, str(parameter.default), f"da {parameter.minimum} a {parameter.maximum}"]
        for parameter in definition.parameters
    ]
    assert shown == [[cell.strip() for cell in row] for row in datatable[1:]]
