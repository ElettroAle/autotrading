from autotrading.domain.sources.source_catalog import SourceCatalog
from autotrading.domain.sources.source_definition import SourceDefinition


class ListSourcesUseCase:
    """The sources a flow can activate, with their parameters (R1.3.1)."""

    def __init__(self, catalog: SourceCatalog) -> None:
        self._catalog = catalog

    def execute(self) -> list[SourceDefinition]:
        return list(self._catalog.sources)
