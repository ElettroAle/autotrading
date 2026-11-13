"""The gateway of OpenRouter: one factory for the call and the catalog of its models (ADR 0109)."""

from autotrading.adapters.outbound.openrouter.composition import openrouter_adapters
from autotrading.adapters.outbound.openrouter.configuration import _OpenRouterSettings
from autotrading.adapters.outbound.openrouter.model_call import TIMEOUT_SECONDS, OpenRouterModelCallAdapter
from autotrading.adapters.outbound.openrouter.model_catalog import OpenRouterModelCatalogAdapter


def test_the_gateway_of_openrouter_is_offered_by_its_name_and_makes_always_the_same_products() -> None:
    gateways = openrouter_adapters()

    assert list(gateways) == ["openrouter"]
    gateway = gateways["openrouter"]
    assert isinstance(gateway.model_call(), OpenRouterModelCallAdapter)
    assert isinstance(gateway.model_catalog(), OpenRouterModelCatalogAdapter)
    assert gateway.model_call() is gateway.model_call()
    assert gateway.model_catalog() is gateway.model_catalog()


def test_the_settings_wait_the_declared_timeout() -> None:
    assert _OpenRouterSettings().timeout_seconds == TIMEOUT_SECONDS
