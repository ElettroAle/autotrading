from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from autotrading.domain.sources.errors import (
    SourceAdapterNotAvailableError,
    SourceAdapterNotFoundError,
    SourceAdapterWithoutConfigurationError,
    SourceNotAvailableError,
    TrialAssetRequiredError,
)
from autotrading.domain.sources.forecast import FORECAST
from autotrading.domain.sources.indicators import INDICATORS
from autotrading.domain.sources.news import NEWS
from autotrading.domain.sources.pivots import PIVOTS
from autotrading.domain.sources.sentiment import SENTIMENT
from autotrading.domain.sources.social import SOCIAL
from autotrading.domain.sources.source_adapter_declaration import SourceAdapterDeclaration
from autotrading.domain.sources.source_definition import SourceDefinition
from autotrading.domain.sources.source_parameter import SourceParameter
from autotrading.domain.sources.volumes import VOLUMES
from autotrading.domain.sources.whale import WHALE

# The sources of the platform: the adapters that offer each one declare themselves (R1.3.1, R4.1.1).
SOURCES = (INDICATORS, PIVOTS, FORECAST, SENTIMENT, NEWS, WHALE, VOLUMES, SOCIAL)


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

    def asset_of_trial(self, asset: str | None) -> str | None:
        """A trial reads a per-asset source for the asset chosen, a market source for the whole market (R6.3.1)."""
        if not self.per_asset:
            return None
        if asset is None or not asset.strip():
            raise TrialAssetRequiredError(self.name)
        return asset.strip()


@dataclass(frozen=True, slots=True)
class ConfigurableAdapter:
    """An adapter that needs configuration, with the sources it offers: the tenant configures it once for all of them
    (R4.1.2).
    """

    declaration: SourceAdapterDeclaration
    sources: tuple[str, ...]

    @property
    def name(self) -> str:
        return self.declaration.name


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

    def configurable_adapters(self) -> tuple[ConfigurableAdapter, ...]:
        """Every adapter that needs configuration once, by name, with the sources it offers (R4.1.2)."""
        sources_of: dict[str, list[str]] = {}
        declarations: dict[str, SourceAdapterDeclaration] = {}
        for source in self._sources:
            for adapter in source.adapters:
                if adapter.needs_configuration:
                    declarations.setdefault(adapter.name, adapter)
                    sources_of.setdefault(adapter.name, []).append(source.name)
        return tuple(ConfigurableAdapter(declarations[name], tuple(sources_of[name])) for name in sorted(declarations))

    def configurable_adapter(self, name: str) -> ConfigurableAdapter:
        """The adapter the tenant gives credentials to; one that needs none, or that no source offers, is refused."""
        for configurable in self.configurable_adapters():
            if configurable.name == name:
                return configurable
        if any(adapter.name == name for source in self._sources for adapter in source.adapters):
            raise SourceAdapterWithoutConfigurationError(name)
        raise SourceAdapterNotFoundError(name)
