from collections.abc import Iterable

from autotrading.domain.sources.errors import SourceNotAvailableError
from autotrading.domain.sources.source_definition import SourceDefinition


class SourceCatalog:
    """The sources of the platform: one added here becomes selectable in the flows with no other change (R1.3.1)."""

    def __init__(self, sources: Iterable[SourceDefinition]) -> None:
        self._sources = tuple(sources)

    @property
    def sources(self) -> tuple[SourceDefinition, ...]:
        return self._sources

    def find(self, name: str) -> SourceDefinition:
        for source in self._sources:
            if source.name == name:
                return source
        raise SourceNotAvailableError(name)
