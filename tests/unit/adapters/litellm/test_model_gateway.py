"""The gateway of the LiteLLM proxy: one factory for the call and the catalog of its routes (ADR 0109)."""

from openai import OpenAI

from autotrading.adapters.outbound.litellm.model_call import LiteLlmModelCallAdapter
from autotrading.adapters.outbound.litellm.model_catalog import LiteLlmModelCatalogAdapter
from autotrading.adapters.outbound.litellm.model_gateway import LiteLlmModelGatewayAdapter


def test_the_gateway_makes_the_call_and_the_catalog_of_the_proxy_always_the_same() -> None:
    gateway = LiteLlmModelGatewayAdapter(OpenAI(api_key="sk-master", base_url="http://litellm:4000", max_retries=0))

    assert isinstance(gateway.model_call(), LiteLlmModelCallAdapter)
    assert isinstance(gateway.model_catalog(), LiteLlmModelCatalogAdapter)
    assert gateway.model_call() is gateway.model_call()
    assert gateway.model_catalog() is gateway.model_catalog()
