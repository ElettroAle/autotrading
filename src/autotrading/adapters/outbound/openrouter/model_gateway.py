import httpx

from autotrading.adapters.outbound.openrouter.model_call import OpenRouterModelCallAdapter
from autotrading.adapters.outbound.openrouter.model_catalog import OpenRouterModelCatalogAdapter


class OpenRouterModelGatewayAdapter:
    """The concrete factory of OpenRouter: the model call and the catalog of its models, one family (ADR 0109)."""

    def __init__(self, client: httpx.Client) -> None:
        self._model_call = OpenRouterModelCallAdapter(client)
        self._model_catalog = OpenRouterModelCatalogAdapter(client)

    def model_call(self) -> OpenRouterModelCallAdapter:
        return self._model_call

    def model_catalog(self) -> OpenRouterModelCatalogAdapter:
        return self._model_catalog
