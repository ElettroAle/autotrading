from dataclasses import dataclass

from autotrading.domain.sources.source_catalog import SourceCatalog
from autotrading.domain.sources.source_definition import SourceDefinition


@dataclass(frozen=True, slots=True)
class GetSourceCommand:
    name: str


class GetSourceUseCase:
    def __init__(self, catalog: SourceCatalog) -> None:
        self._catalog = catalog

    def execute(self, command: GetSourceCommand) -> SourceDefinition:
        return self._catalog.find(command.name)
