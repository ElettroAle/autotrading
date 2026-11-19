from collections.abc import Mapping
from dataclasses import dataclass

from autotrading.application.sources.collect_source import (
    CollectedSource,
    CollectSourceCommand,
    CollectSourceUseCase,
)
from autotrading.application.sources.errors import SourceCredentialsRejectedError
from autotrading.application.sources.list_sources import ListSourcesUseCase, SourceSystems
from autotrading.application.sources.open_source_credentials import OpenSourceCredentialsUseCase
from autotrading.application.sources.ports import (
    CycleSourceAskPort,
    ForecastRepositoryPort,
    SampleRepositoryPort,
    SourceCredentialsRejectionNoticePort,
    SourceCredentialsRepositoryPort,
    SourceSecretsOpenerPort,
)
from autotrading.application.sources.record_source_credentials_rejection import (
    RecordSourceCredentialsRejectionUseCase,
)
from autotrading.application.sources.source_readers import readers_of
from autotrading.domain.sources.source_catalog import SourceCatalog
from autotrading.domain.sources.source_sample import CycleReference


@dataclass(frozen=True, slots=True)
class SourceCredentialServices:
    """What the worker needs for the credentials of the adapters of a tenant: the saved ones, the opener only the worker
    holds, and the notice of a refusal of the provider (R4.1.2, ADR credenziali-degli-adapter-delle-fonti)."""

    repository: SourceCredentialsRepositoryPort
    opener: SourceSecretsOpenerPort
    rejection_notice: SourceCredentialsRejectionNoticePort


class CollectCycleSourceUseCase:
    """Collects an adapter of an active source of a flow for one cycle and records it for the tenant (R1.3.2-R1.3.8,
    R4.1.1, ADR 0042).

    The readers depend on the cycle: the indicators read candles of the cycle interval of the flow (R1.3.3). Every
    reader is registered by its source and by the name the adapter declares. An adapter that needs configuration reads
    with the credentials of the tenant; when the provider refuses them the refusal is kept and told once, and the
    adapter stays absent from the cycle (R4.1.2).
    """

    def __init__(
        self,
        systems: SourceSystems,
        forecasts: ForecastRepositoryPort,
        samples: SampleRepositoryPort,
        credentials: SourceCredentialServices,
    ) -> None:
        self._systems = systems
        self._forecasts = forecasts
        self._samples = samples
        self._credentials = credentials

    def execute(self, ask: CycleSourceAskPort) -> CollectedSource:
        catalog = ListSourcesUseCase(self._systems).execute()
        command = CollectSourceCommand(
            CycleReference(ask.flow_id, ask.planned_at),
            ask.source,
            ask.adapter,
            ask.weight,
            ask.parameters,
            ask.assets,
            ask.asked_at,
            self._credentials_of(catalog, ask),
        )
        return self._collected(catalog, command, ask.cycle_minutes)

    def _credentials_of(self, catalog: SourceCatalog, ask: CycleSourceAskPort) -> Mapping[str, str]:
        adapter = catalog.find(ask.source).adapter(ask.adapter)
        return OpenSourceCredentialsUseCase(self._credentials.repository, self._credentials.opener).execute(adapter)

    def _collected(self, catalog: SourceCatalog, command: CollectSourceCommand, cycle_minutes: int) -> CollectedSource:
        collect = CollectSourceUseCase(
            catalog, readers_of(self._systems, self._forecasts, cycle_minutes), self._samples
        )
        try:
            return collect.execute(command)
        except SourceCredentialsRejectedError:
            # The refusal stays the reason of the absent adapter: it is kept and told, then raised again.
            RecordSourceCredentialsRejectionUseCase(
                self._credentials.repository, self._credentials.rejection_notice
            ).execute(command.adapter, command.collected_at)
            raise
