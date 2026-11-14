"""The gateway of the LiteLLM library: one factory for the call and the catalog of the same models (ADR 0109, 0148)."""

from collections.abc import Sequence

from autotrading.adapters.outbound.litellm.model_call import LiteLlmModelCallAdapter
from autotrading.adapters.outbound.litellm.model_catalog import LiteLlmModelCatalogAdapter, _ModelLibrary
from autotrading.adapters.outbound.litellm.model_gateway import LiteLlmModelGatewayAdapter


def _completion(**_request: object) -> object:
    return None


def _parameters_of(_model: str, _provider: str) -> Sequence[str] | None:
    return None


def _required_keys(_model: str) -> Sequence[str]:
    return []


def test_the_gateway_makes_the_call_and_the_catalog_of_the_library_always_the_same() -> None:
    gateway = LiteLlmModelGatewayAdapter(
        _completion, _ModelLibrary({}, _parameters_of, _required_keys), frozenset({"openai"}), 120.0
    )

    assert isinstance(gateway.model_call(), LiteLlmModelCallAdapter)
    assert isinstance(gateway.model_catalog(), LiteLlmModelCatalogAdapter)
    assert gateway.model_call() is gateway.model_call()
    assert gateway.model_catalog() is gateway.model_catalog()
