from autotrading.application.agent.model_gateways import ModelCatalogs, joined_catalog
from autotrading.domain.agent.model_catalog import ModelCatalog


class ReadModelCatalogUseCase:
    """The models of the gateways the worker alone holds, as the API asks for them (R1.4.2, ADR 0149).

    The same for every tenant: the catalog depends on no key.
    """

    def __init__(self, catalogs: ModelCatalogs) -> None:
        self._catalogs = catalogs

    def execute(self) -> ModelCatalog:
        return joined_catalog(self._catalogs)
