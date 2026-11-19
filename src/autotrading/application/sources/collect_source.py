from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime

from autotrading.application.sources.ports import SampleRepositoryPort, SourceReaderPort, SourceRequest
from autotrading.domain.sources.errors import SourceAdapterNotAvailableError
from autotrading.domain.sources.source_catalog import OfferedSource, SourceCatalog
from autotrading.domain.sources.source_sample import CycleReference, SourceSample

# A reader reads one adapter of one source: the source and the adapter name it (R4.1.1).
type Reader = tuple[str, str]


@dataclass(frozen=True, slots=True)
class CollectSourceCommand:
    """An adapter of an active source of the flow, as its configuration selects it, in one cycle (R1.3.2, R4.1.1)."""

    cycle: CycleReference
    source: str
    adapter: str
    weight: int
    parameters: Mapping[str, int]
    assets: tuple[str, ...]
    collected_at: datetime
    # What the worker opened of the credentials of the adapter, none when it declares no field (R4.1.2).
    credentials: Mapping[str, str] = field(default_factory=dict, repr=False)


@dataclass(frozen=True, slots=True)
class CollectedSource:
    """The values one adapter of an active source read in the cycle, with the weight the agent receives (R1.3.2).

    A source that collected nothing may still have a note for the agent (R1.3.7); it is never recorded as a sample.
    """

    source: str
    adapter: str
    weight: int
    samples: tuple[SourceSample, ...]
    note: Mapping[str, str] | None = None

    @property
    def entries(self) -> tuple[tuple[str | None, Mapping[str, str]], ...]:
        """What the agent reads of the source: each value with its asset, or the note of its silence (R1.3.7)."""
        values = tuple((sample.asset, sample.values) for sample in self.samples)
        if self.note is None:
            return values
        return (*values, (None, self.note))


class CollectSourceUseCase:
    """Reads an adapter of an active source for every asset of the flow, or once for the market, and records what it
    collected.

    The parameters the flow does not set take the default of the catalog (R1.3.2); every value is recorded with its
    adapter, its reference instant and the instant of the collection (R1.3.8, R4.1.1).
    """

    def __init__(
        self, catalog: SourceCatalog, readers: Mapping[Reader, SourceReaderPort], samples: SampleRepositoryPort
    ) -> None:
        self._catalog = catalog
        self._readers = readers
        self._samples = samples

    def execute(self, command: CollectSourceCommand) -> CollectedSource:
        offered = self._catalog.find(command.source)
        settings = offered.settings(command.adapter, command.parameters)
        reader = self._reader_of(offered, command.adapter)
        named = (offered.name, command.adapter)
        samples = tuple(
            SourceSample.of(command.cycle, named, asset, value, command.collected_at)
            for asset in _targets_of(offered, command.assets)
            for value in reader.execute(
                SourceRequest(command.cycle.flow_id, asset, settings, command.collected_at, command.credentials)
            )
        )
        self._samples.add(samples)
        note = None if samples else offered.definition.silence_note(settings)
        return CollectedSource(offered.name, command.adapter, command.weight, samples, note)

    def _reader_of(self, offered: OfferedSource, adapter: str) -> SourceReaderPort:
        reader = self._readers.get((offered.name, adapter))
        if reader is None:
            raise SourceAdapterNotAvailableError(offered.name, adapter)
        return reader


def _targets_of(offered: OfferedSource, assets: tuple[str, ...]) -> tuple[str | None, ...]:
    if offered.per_asset:
        return assets
    return (None,)
