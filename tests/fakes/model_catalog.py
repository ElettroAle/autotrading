"""The catalog of the models in memory, as the model gateway would describe it (ADR 0103)."""

from autotrading.application.agent.errors import ModelCatalogUnavailableError
from autotrading.application.flows.errors import FlowModelCatalogUnavailableError
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.provider_name import ProviderName


class InMemoryModelCatalogAdapter:
    """Realises the catalog port of the agent and the models port of the flows over a fixed catalog."""

    def __init__(
        self, catalog: ModelCatalog, *, available: bool = True, reading_expiry: frozenset[str] = frozenset()
    ) -> None:
        self._catalog = catalog
        self._available = available
        # The providers whose keys the gateway tells the expiry of: none, unless a test says so (R6.2.2).
        self._reading_expiry = reading_expiry

    def reads_key_expiry(self, provider: ProviderName) -> bool:
        return provider.value in self._reading_expiry

    def catalog(self) -> ModelCatalog:
        if not self._available:
            raise ModelCatalogUnavailableError
        return self._catalog

    def definition_of(self, model: str) -> ModelDefinition:
        if not self._available:
            raise FlowModelCatalogUnavailableError
        return self._catalog.find(model)
