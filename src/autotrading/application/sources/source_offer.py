from dataclasses import dataclass

from autotrading.domain.sources.source_adapter_declaration import SourceAdapterDeclaration
from autotrading.domain.sources.source_catalog import OfferedSource


@dataclass(frozen=True, slots=True)
class SourceOffer:
    """A source of the catalog as a tenant may activate it: an adapter that needs configuration the tenant did not give
    stays in the list, not activatable, with the reason (R4.1.2)."""

    source: OfferedSource
    configured_adapters: frozenset[str]

    def configured(self, adapter: SourceAdapterDeclaration) -> bool | None:
        """Whether the tenant configured the adapter; None when it needs no configuration."""
        if not adapter.needs_configuration:
            return None
        return adapter.name in self.configured_adapters

    def missing_configuration(self, adapter: SourceAdapterDeclaration) -> str | None:
        return adapter.missing_configuration(self.configured_adapters)
