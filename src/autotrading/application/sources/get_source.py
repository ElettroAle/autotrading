from dataclasses import dataclass

from autotrading.application.sources.list_sources import ListSourcesUseCase
from autotrading.domain.sources.source_catalog import OfferedSource


@dataclass(frozen=True, slots=True)
class GetSourceCommand:
    name: str


class GetSourceUseCase:
    """One source of the catalog with its adapters (R1.3.1, R4.1.1)."""

    def __init__(self, sources: ListSourcesUseCase) -> None:
        self._sources = sources

    def execute(self, command: GetSourceCommand) -> OfferedSource:
        return self._sources.execute().find(command.name)
