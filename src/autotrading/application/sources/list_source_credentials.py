from collections.abc import Callable
from datetime import datetime

from autotrading.application.sources.list_sources import ListSourcesUseCase
from autotrading.application.sources.ports import SourceCredentialsRepositoryPort
from autotrading.application.sources.source_credentials_summary import SourceCredentialsSummary
from autotrading.domain.sources.key_expiry import utc_day_of


class ListSourceCredentialsUseCase:
    """The adapters of the sources that need configuration, each with the credentials the tenant gave it as of today;
    an adapter that needs none is not listed, and the secrets never leave the database (R4.1.2, R6.2.2).
    """

    def __init__(
        self,
        sources: ListSourcesUseCase,
        credentials: SourceCredentialsRepositoryPort,
        clock: Callable[[], datetime],
    ) -> None:
        self._sources = sources
        self._credentials = credentials
        self._clock = clock

    def execute(self) -> list[SourceCredentialsSummary]:
        today = utc_day_of(self._clock())
        registrations = {each.credentials.adapter: each for each in self._credentials.registrations()}
        return [
            SourceCredentialsSummary.of(adapter, registrations.get(adapter.name), today)
            for adapter in self._sources.execute().configurable_adapters()
        ]
