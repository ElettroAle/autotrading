from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime

from autotrading.application.sources.list_sources import ListSourcesUseCase, SourceSystems
from autotrading.application.sources.open_source_credentials import OpenSourceCredentialsUseCase
from autotrading.application.sources.ports import (
    ClockPort,
    ConcurrentCallsPort,
    ForecastRepositoryPort,
    SourceRequest,
    TrialIntervalPort,
)
from autotrading.application.sources.source_readers import readers_of
from autotrading.domain.errors import AutotradingError
from autotrading.domain.sources.errors import SourceAdapterNotAvailableError
from autotrading.domain.sources.source_catalog import OfferedSource
from autotrading.domain.sources.source_sample import SourceValue
from autotrading.domain.sources.source_trial import SourceTrial

MILLISECONDS_PER_SECOND = 1000


@dataclass(frozen=True, slots=True)
class TrySourceAdapterCommand:
    source: str
    adapter: str
    # None for a source of the whole market.
    asset: str | None = None
    parameters: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TrialServices:
    """What a trial reads as a cycle does: the concurrent calls with the wait of the sources, and the clock that times
    the answer (R1.2.5, R6.3.1)."""

    calls: ConcurrentCallsPort
    clock: ClockPort
    interval: TrialIntervalPort


class TrySourceAdapterUseCase:
    """Reads an adapter of a source now, with the reader, the credentials and the wait of a cycle, and records nothing
    (R6.3.1, ADR prova-di-un-adapter-di-fonte-nel-worker).

    An unknown source or adapter and a parameter outside its values are refused before reading; whatever stops the
    reading is the outcome of the trial, transient or permanent as in a cycle (R1.2.5).
    """

    def __init__(
        self,
        systems: SourceSystems,
        forecasts: ForecastRepositoryPort,
        credentials: OpenSourceCredentialsUseCase,
        services: TrialServices,
    ) -> None:
        self._systems = systems
        self._forecasts = forecasts
        self._credentials = credentials
        self._services = services

    def execute(self, command: TrySourceAdapterCommand) -> SourceTrial:
        offered = ListSourcesUseCase(self._systems).execute().find(command.source)
        settings = offered.settings(command.adapter, command.parameters)
        asset = offered.asset_of_trial(command.asset)
        started_at = self._services.clock.now()
        try:
            values = self._read(offered, command.adapter, SourceRequest(None, asset, settings, started_at))
        except AutotradingError as error:
            return SourceTrial.failed(str(error), error.permanent, self._milliseconds_since(started_at))
        return SourceTrial.succeeded(tuple(values), self._milliseconds_since(started_at))

    def _read(self, offered: OfferedSource, adapter: str, request: SourceRequest) -> Sequence[SourceValue]:
        credentials = self._credentials.execute(offered.adapter(adapter))
        readers = readers_of(self._systems, self._forecasts, self._services.interval.minutes)
        reader = readers.get((offered.name, adapter))
        if reader is None:
            raise SourceAdapterNotAvailableError(offered.name, adapter)
        opened = replace(request, credentials=credentials)
        return self._services.calls.call_within(
            lambda: reader.execute(opened), self._services.interval.source_wait.total_seconds()
        )

    def _milliseconds_since(self, started_at: datetime) -> int:
        elapsed = self._services.clock.now() - started_at
        return max(0, round(elapsed.total_seconds() * MILLISECONDS_PER_SECOND))
