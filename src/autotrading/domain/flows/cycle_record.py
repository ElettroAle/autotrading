from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.cycle_trigger import CycleTrigger
from autotrading.domain.flows.errors import UnknownCycleOutcomeError
from autotrading.domain.flows.recorded_decision import RecordedDecision


class CycleOutcome(StrEnum):
    COMPLETED = "concluso"
    FAILED = "fallito"
    SKIPPED = "saltato"

    @classmethod
    def named(cls, name: str) -> CycleOutcome:
        """The outcome by the word the consultation shows (R6.4.2)."""
        outcomes = {outcome.value: outcome for outcome in cls}
        if name not in outcomes:
            raise UnknownCycleOutcomeError(tuple(outcomes))
        return outcomes[name]


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
class StepDocument:
    """What one step produced, as JSON data described by the context behind the step (R1.7.1)."""

    step: CycleStep
    content: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class CycleRecord:
    """What a cycle produced up to the last step it ran, and what started it (R1.2.1-R1.2.5, R1.7.1, R6.5.2), with the
    decisions of the agent one by asset when it got to them (R6.5.4).
    """

    flow_id: UUID
    planned_at: datetime
    outcome: CycleOutcome
    started_at: datetime | None = None
    delay_seconds: int | None = None
    steps: tuple[CycleStep, ...] = ()
    absent_sources: tuple[AbsentSource, ...] = ()
    failure: CycleFailure | None = None
    documents: tuple[StepDocument, ...] = ()
    cost: CallCost | None = None
    decisions: tuple[RecordedDecision, ...] = ()
    trigger: CycleTrigger = CycleTrigger.SCHEDULED

    @classmethod
    def skipped(cls, flow_id: UUID, planned_at: datetime) -> CycleRecord:
        """A cycle planned while the previous one was still running (R1.2.2)."""
        return cls(flow_id, planned_at, CycleOutcome.SKIPPED)

    def document(self, step: CycleStep) -> Mapping[str, object] | None:
        """What the step produced in this cycle; None when the cycle never got to it."""
        return next((document.content for document in self.documents if document.step is step), None)
