from autotrading.application.sources.list_sources import ListSourcesUseCase
from autotrading.application.sources.ports import SourceCredentialsRepositoryPort
from autotrading.application.sources.source_offer import SourceOffer


class ListSourceOffersUseCase:
    """The sources a flow of the tenant can activate, each with its adapters and, for those that need configuration,
    whether the tenant gave it (R1.3.1, R4.1.1, R4.1.2)."""

    def __init__(self, sources: ListSourcesUseCase, credentials: SourceCredentialsRepositoryPort) -> None:
        self._sources = sources
        self._credentials = credentials

    def execute(self) -> tuple[SourceOffer, ...]:
        configured = frozenset(each.credentials.adapter for each in self._credentials.registrations())
        return tuple(SourceOffer(source, configured) for source in self._sources.execute().sources)
