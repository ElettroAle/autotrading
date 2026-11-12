from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from autotrading.domain.cycles.cycle_step import CycleStep


class CycleOutcome(StrEnum):
    COMPLETED = "concluso"
    FAILED = "fallito"
    SKIPPED = "saltato"


@dataclass(frozen=True, slots=True)
class CycleFailure:
    """Where the cycle stopped and why, with the original message of the error (R1.2.3)."""

    step: CycleStep
    error_type: str
    message: str


@dataclass(frozen=True, slots=True)
class AbsentSource:
    """A source that gave no data in the cycle, with the reason declared to the agent (R1.2.5)."""

    source: str
    reason: str


@dataclass(frozen=True, slots=True)
class CycleRecord:
    """What a cycle produced up to the last step it ran (R1.2.1-R1.2.5)."""

    flow_id: UUID
    planned_at: datetime
    outcome: CycleOutcome
    started_at: datetime | None = None
    delay_seconds: int | None = None
    steps: tuple[CycleStep, ...] = ()
    absent_sources: tuple[AbsentSource, ...] = ()
    failure: CycleFailure | None = None

    @classmethod
    def skipped(cls, flow_id: UUID, planned_at: datetime) -> CycleRecord:
        """A cycle planned while the previous one was still running (R1.2.2)."""
        return cls(flow_id, planned_at, CycleOutcome.SKIPPED)
