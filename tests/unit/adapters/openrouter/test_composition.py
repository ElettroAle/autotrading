"""The gateway of OpenRouter: one factory for the call and the catalog of its models (ADR 0109)."""

from autotrading.adapters.outbound.openrouter.composition import openrouter_adapters
from autotrading.adapters.outbound.openrouter.configuration import _OpenRouterSettings
from autotrading.adapters.outbound.openrouter.model_call import TIMEOUT_SECONDS, OpenRouterModelCallAdapter
from autotrading.adapters.outbound.openrouter.model_catalog import OpenRouterModelCatalogAdapter


def test_the_gateway_makes_the_call_and_the_catalog_of_openrouter_always_the_same() -> None:
    gateway = openrouter_adapters()

    assert isinstance(gateway.model_call(), OpenRouterModelCallAdapter)
    assert isinstance(gateway.model_catalog(), OpenRouterModelCatalogAdapter)
    assert gateway.model_call() is gateway.model_call()
    assert gateway.model_catalog() is gateway.model_catalog()


def test_the_settings_wait_the_declared_timeout() -> None:
    assert _OpenRouterSettings().timeout_seconds == TIMEOUT_SECONDS
