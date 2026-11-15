from autotrading.adapters.outbound.litellm.model_call import Completion, LiteLlmModelCallAdapter, StrictFormatSupport
from autotrading.adapters.outbound.litellm.model_catalog import (
    LiteLlmModelCatalogAdapter,
    _ModelLibrary,
)


class LiteLlmModelGatewayAdapter:
    """The concrete factory of the LiteLLM library: the model call and the catalog of its models (ADR 0109, 0148)."""

    def __init__(
        self,
        completion: Completion,
        supports_strict_format: StrictFormatSupport,
        library: _ModelLibrary,
        providers: frozenset[str],
        timeout_seconds: float,
    ) -> None:
        self._model_call = LiteLlmModelCallAdapter(completion, supports_strict_format, timeout_seconds)
        self._model_catalog = LiteLlmModelCatalogAdapter(library, providers)

    def model_call(self) -> LiteLlmModelCallAdapter:
        return self._model_call

    def model_catalog(self) -> LiteLlmModelCatalogAdapter:
        return self._model_catalog
