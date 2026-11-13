"""The catalog of the models in memory, as the model gateway would describe it (ADR 0103)."""

from autotrading.application.agent.errors import ModelCatalogUnavailableError
from autotrading.application.flows.errors import FlowModelCatalogUnavailableError
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.agent.model_definition import ModelDefinition


class InMemoryModelCatalogAdapter:
    """Realises the catalog port of the agent and the models port of the flows over a fixed catalog."""

    def __init__(self, catalog: ModelCatalog, *, available: bool = True) -> None:
        self._catalog = catalog
        self._available = available

    def catalog(self) -> ModelCatalog:
        if not self._available:
            raise ModelCatalogUnavailableError
        return self._catalog

    def definition_of(self, model: str) -> ModelDefinition:
        if not self._available:
            raise FlowModelCatalogUnavailableError
        return self._catalog.find(model)
