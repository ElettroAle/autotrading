from openai import OpenAI

from autotrading.adapters.outbound.litellm.model_call import LiteLlmModelCallAdapter
from autotrading.adapters.outbound.litellm.model_catalog import LiteLlmModelCatalogAdapter


class LiteLlmModelGatewayAdapter:
    """The concrete factory of the LiteLLM proxy: the model call and the catalog of its routes (ADR 0109)."""

    def __init__(self, client: OpenAI) -> None:
        self._model_call = LiteLlmModelCallAdapter(client)
        self._model_catalog = LiteLlmModelCatalogAdapter(client)

    def model_call(self) -> LiteLlmModelCallAdapter:
        return self._model_call

    def model_catalog(self) -> LiteLlmModelCatalogAdapter:
        return self._model_catalog
