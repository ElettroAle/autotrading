from decimal import Decimal

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.agent.list_models import ModelListing
from autotrading.application.agent.register_provider_key import RegisterProviderKeyCommand
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.model_parameter import RangeParameter
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios("E1-flussi-autonomi/F1.4-agente-ia/R1.4.2-catalogo-dei-modelli.feature")

KEY = "K-REGISTERED"


@pytest.fixture
def platform() -> Platform:
    return Platform()


@pytest.fixture
def consulted() -> dict[str, ModelListing]:
    return {}


@given(
    quoted(
        'che il catalogo contiene il modello "{model}" con temperatura da {minimum} a {maximum}, predefinita {default}'
    )
)
def catalog_with(platform: Platform, model: str, minimum: str, maximum: str, default: str) -> None:
    temperature = RangeParameter("temperature", Decimal(minimum), Decimal(maximum), Decimal(default))
    platform.model_catalog = ModelCatalog((ModelDefinition(model, (temperature,)),))


@given(quoted('che "{user}" ha registrato la chiave del fornitore "{provider}"'))
def key_registered(platform: Platform, user: str, provider: str) -> None:
    platform.providers.accept(provider, KEY)
    platform.use_cases_of(user).register_provider_key.execute(RegisterProviderKeyCommand(provider, KEY))


@when(quoted('"{user}" consulta il catalogo dei modelli'))
def consult(platform: Platform, user: str, consulted: dict[str, ModelListing]) -> None:
    consulted["catalog"] = platform.use_cases_of(user).list_models.execute()


@then(
    quoted(
        'il catalogo contiene il modello "{model}" con il parametro {label} '
        "da {minimum} a {maximum}, predefinita {default}"
    )
)
def catalog_shows(
    consulted: dict[str, ModelListing], model: str, label: str, *, minimum: str, maximum: str, default: str
) -> None:
    (definition,) = [entry for entry in consulted["catalog"].models if entry.name == model]
    shown = [
        (parameter.label, str(parameter.minimum), str(parameter.maximum), str(parameter.default))
        for parameter in definition.parameters
        if isinstance(parameter, RangeParameter)
    ]
    assert shown == [(label, minimum, maximum, default)]


@then(quoted('il fornitore "{provider}" risulta con chiave registrata'))
def provider_has_key(consulted: dict[str, ModelListing], provider: str) -> None:
    listed = {listing.provider.value: listing.key_registered for listing in consulted["catalog"].providers}
    assert listed == {provider: True}
