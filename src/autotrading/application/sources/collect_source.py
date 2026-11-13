from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from autotrading.application.sources.ports import ReadSourceCommand, SampleRepositoryPort, SourceReaderPort
from autotrading.domain.sources.errors import SourceNotAvailableError
from autotrading.domain.sources.source_catalog import SourceCatalog
from autotrading.domain.sources.source_definition import SourceDefinition
from autotrading.domain.sources.source_sample import CycleReference, SourceSample


@dataclass(frozen=True, slots=True)
class CollectSourceCommand:
    """An active source of the flow, as its configuration selects it, in one cycle (R1.3.2)."""

    cycle: CycleReference
    source: str
    weight: int
    parameters: Mapping[str, int]
    assets: tuple[str, ...]
    collected_at: datetime


@dataclass(frozen=True, slots=True)
class CollectedSource:
    """The values of one active source in the cycle, with the weight the agent receives (R1.3.2).

    A source that collected nothing may still have a note for the agent (R1.3.7); it is never recorded as a sample.
    """

    source: str
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
    """Reads an active source for every asset of the flow, or once for the market, and records what it collected.

    The parameters the flow does not set take the default of the catalog (R1.3.2); every value is recorded with its
    reference instant and the instant of the collection (R1.3.8).
    """

    def __init__(
        self, catalog: SourceCatalog, readers: Mapping[str, SourceReaderPort], samples: SampleRepositoryPort
    ) -> None:
        self._catalog = catalog
        self._readers = readers
        self._samples = samples

    def execute(self, command: CollectSourceCommand) -> CollectedSource:
        definition = self._catalog.find(command.source)
        reader = self._reader_of(definition)
        settings = definition.settings(command.parameters)
        samples = tuple(
            SourceSample.of(command.cycle, definition.name, asset, value, command.collected_at)
            for asset in _targets_of(definition, command.assets)
            for value in reader.execute(ReadSourceCommand(command.cycle.flow_id, asset, settings, command.collected_at))
        )
        self._samples.add(samples)
        note = None if samples else definition.silence_note(settings)
        return CollectedSource(definition.name, command.weight, samples, note)

    def _reader_of(self, definition: SourceDefinition) -> SourceReaderPort:
        reader = self._readers.get(definition.name)
        if reader is None:
            raise SourceNotAvailableError(definition.name)
        return reader


def _targets_of(definition: SourceDefinition, assets: tuple[str, ...]) -> tuple[str | None, ...]:
    if definition.per_asset:
        return assets
    return (None,)
