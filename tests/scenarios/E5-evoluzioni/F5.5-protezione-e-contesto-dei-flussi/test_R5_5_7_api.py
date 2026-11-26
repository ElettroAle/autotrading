"""R5.5.7: the lists of the sources and of the models give a description of every parameter, the text of its info button
(ADR descrizioni-dei-parametri-di-fonti-e-modelli).
"""

import pytest
from pytest_bdd import scenarios, then, when

from autotrading.adapters.inbound.api.models import ModelCatalogResponse
from autotrading.adapters.inbound.api.sources import SourceResponse
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios(
    "E5-evoluzioni/F5.5-protezione-e-contesto-dei-flussi/R5.5.7-informazioni-sui-campi/api/R5.5.7-informazioni-sui-campi.feature"
)


@pytest.fixture
def platform() -> Platform:
    return Platform()


@pytest.fixture
def listed() -> dict[str, object]:
    return {}


@when(quoted('"{user}" legge l\'elenco delle fonti con i loro adapter'))
def read_sources(platform: Platform, listed: dict[str, object], user: str) -> None:
    listed["sources"] = [SourceResponse.of(offer) for offer in platform.use_cases_of(user).list_source_offers.execute()]


@then("ogni parametro di ogni adapter riporta una descrizione non vuota")
def every_adapter_parameter_described(listed: dict[str, object]) -> None:
    sources = listed["sources"]
    assert isinstance(sources, list)
    parameters = [
        (adapter.name, parameter.key, parameter.description.strip() != "")
        for source in sources
        for adapter in source.adapters
        for parameter in adapter.parameters
    ]
    assert parameters
    assert [parameter for parameter in parameters if not parameter[2]] == []


@when(quoted('"{user}" legge l\'elenco dei modelli con i loro parametri'))
def read_models(platform: Platform, listed: dict[str, object], user: str) -> None:
    listed["models"] = ModelCatalogResponse.of(platform.use_cases_of(user).list_models.execute())


@then("ogni parametro di ogni modello riporta una descrizione non vuota")
def every_model_parameter_described(listed: dict[str, object]) -> None:
    catalog = listed["models"]
    assert isinstance(catalog, ModelCatalogResponse)
    parameters = [
        (model.name, parameter.key, parameter.description.strip() != "")
        for model in catalog.models
        for parameter in model.parameters
    ]
    assert {key for _, key, _ in parameters} == {"temperature", "max_tokens", "reasoning_effort"}
    assert [parameter for parameter in parameters if not parameter[2]] == []
