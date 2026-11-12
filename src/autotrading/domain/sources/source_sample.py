from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from autotrading.domain.sources.errors import InvalidSourceSampleError


@dataclass(frozen=True, slots=True)
class SourceValue:
    """What a source read for one asset, or for the whole market, and the instant the data refers to (R1.3.8).

    The reference instant belongs to the data, such as the close of a candle or the publication of a story.
    """

    reference_at: datetime
    values: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class CycleReference:
    """The cycle that collected the data: a cycle is the planned instant of its flow (ADR 0041)."""

    flow_id: UUID
    planned_at: datetime


@dataclass(frozen=True, slots=True)
class SourceSample:
    """One value collected by a source in a cycle, kept for replays and analyses (R1.3.8)."""

    cycle: CycleReference
    source: str
    asset: str | None
    reference_at: datetime
    collected_at: datetime
    values: Mapping[str, str]

    def __post_init__(self) -> None:
        instants = (self.cycle.planned_at, self.reference_at, self.collected_at)
        if any(instant.tzinfo is None for instant in instants):
            raise InvalidSourceSampleError

    @classmethod
    def of(
        cls, cycle: CycleReference, source: str, asset: str | None, value: SourceValue, collected_at: datetime
    ) -> SourceSample:
        return cls(cycle, source, asset, value.reference_at, collected_at, dict(value.values))
