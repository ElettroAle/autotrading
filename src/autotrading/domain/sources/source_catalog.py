from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from autotrading.domain.sources.errors import SourceAdapterNotAvailableError, SourceNotAvailableError
from autotrading.domain.sources.forecast import FORECAST
from autotrading.domain.sources.indicators import INDICATORS
from autotrading.domain.sources.news import NEWS
from autotrading.domain.sources.pivots import PIVOTS
from autotrading.domain.sources.sentiment import SENTIMENT
from autotrading.domain.sources.source_adapter_declaration import SourceAdapterDeclaration
from autotrading.domain.sources.source_definition import SourceDefinition
from autotrading.domain.sources.source_parameter import SourceParameter

# The sources of the platform: the adapters that offer each one declare themselves (R1.3.1, R4.1.1).
SOURCES = (INDICATORS, PIVOTS, FORECAST, SENTIMENT, NEWS)


@dataclass(frozen=True, slots=True)
class OfferedSource:
    """A source with the adapters that offer it: the flow activates it choosing one or more of them (R4.1.1)."""

    definition: SourceDefinition
    adapters: tuple[SourceAdapterDeclaration, ...]

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def description(self) -> str:
        return self.definition.description

    @property
    def per_asset(self) -> bool:
        return self.definition.per_asset

    def adapter(self, name: str) -> SourceAdapterDeclaration:
        for adapter in self.adapters:
            if adapter.name == name:
                return adapter
        raise SourceAdapterNotAvailableError(self.name, name)

    def parameters_of(self, adapter: str) -> tuple[SourceParameter, ...]:
        """The rules of the source hold for every adapter; an adapter may add parameters of its own (R4.1.1)."""
        return (*self.definition.parameters, *self.adapter(adapter).parameters)

    def settings(self, adapter: str, requested: Mapping[str, int]) -> dict[str, int]:
        """The parameters of an adapter of the flow: the requested values checked, the defaults for the others."""
        return self.definition.settings(requested, self.adapter(adapter).parameters)


class SourceCatalog:
    """The sources a flow can activate, each with its adapters: a source or an adapter added becomes selectable in the
    flows with no other change (R1.3.1, R4.1.1).
    """

    def __init__(self, sources: Iterable[OfferedSource]) -> None:
        self._sources = tuple(sources)

    @property
    def sources(self) -> tuple[OfferedSource, ...]:
        return self._sources

    def find(self, name: str) -> OfferedSource:
        for source in self._sources:
            if source.name == name:
                return source
        raise SourceNotAvailableError(name)
