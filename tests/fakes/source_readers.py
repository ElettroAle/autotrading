from collections.abc import Sequence

from autotrading.application.sources.ports import SourceRequest
from autotrading.domain.sources.source_sample import SourceSample, SourceValue


class FakeSourceReaderAdapter:
    """A source that answers the same values to every reading, and remembers each reading it received."""

    def __init__(self, values: Sequence[SourceValue] = ()) -> None:
        self.values = list(values)
        self.readings: list[SourceRequest] = []

    def execute(self, command: SourceRequest) -> list[SourceValue]:
        self.readings.append(command)
        return self.values


class InMemorySampleRepositoryAdapter:
    """The values collected by the cycles of one tenant, as the database records them."""

    def __init__(self) -> None:
        self.samples: list[SourceSample] = []

    def add(self, samples: Sequence[SourceSample]) -> None:
        self.samples.extend(samples)
