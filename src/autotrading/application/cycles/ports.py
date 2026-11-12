from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from autotrading.domain.cycles.call_cost import CallCost
from autotrading.domain.cycles.cycle_record import AbsentSource, CycleRecord
from autotrading.domain.cycles.cycle_schedule import CycleSchedule
from autotrading.domain.cycles.cycle_step import CycleStep
from autotrading.domain.cycles.flow_cost import CycleCost
from autotrading.domain.errors import AutotradingError


@dataclass(frozen=True, slots=True)
class ScheduledFlow:
    """An active flow with the schedule that starts at its last start or resume (R1.2.1)."""

    flow_id: UUID
    schedule: CycleSchedule


@dataclass(frozen=True, slots=True)
class FlowSnapshot:
    """The state of the flow read at the start of the cycle; the cycle only needs the names of its active sources.

    The state itself belongs to the flow and travels to the context and the risk check as it is (ADR 0041).
    """

    sources: tuple[str, ...]
    state: object


@dataclass(frozen=True, slots=True)
class SourceReading:
    source: str
    data: object


@dataclass(frozen=True, slots=True)
class RiskReview:
    """The orders the risk check approved, and the outcome of every decision; the execution orders them (R1.5.5).

    The outcomes travel only to the record: approved, reduced, blocked or discarded (R1.7.1).
    """

    orders: tuple[object, ...]
    outcomes: object


class ClockPort(Protocol):
    def now(self) -> datetime: ...


class ScheduledFlowsPort(Protocol):
    def active(self) -> list[ScheduledFlow]:
        """Every active flow of every tenant: the worker plans the cycles of the whole installation."""
        ...


class CycleRepositoryPort(Protocol):
    def claim(self, flow_id: UUID, planned_at: datetime) -> bool:
        """Takes the planned instant of the flow for this executor; False when another one already took it."""
        ...

    def record(self, record: CycleRecord) -> None: ...


class FlowLockPort(Protocol):
    def hold(self, flow_id: UUID) -> AbstractContextManager[bool]:
        """Holds the flow for one cycle, across processes; yields False at once when a cycle is still running."""
        ...


class CycleLauncherPort(Protocol):
    def launch(self, task: Callable[[], object]) -> None:
        """Runs the cycle apart from the others, so a slow flow never delays another (R1.2.1)."""
        ...


class FlowStatePort(Protocol):
    def read(self, flow_id: UUID) -> FlowSnapshot: ...

    def update(self, flow_id: UUID, executions: Sequence[object]) -> object:
        """Applies the executions of the cycle and gives back the state of the flow at the end of it."""
        ...


class SourcePort(Protocol):
    def collect(self, flow_id: UUID, planned_at: datetime, source: str) -> object:
        """The data of one active source; any typed error makes the source absent for the cycle (R1.2.5)."""
        ...


class ContextPort(Protocol):
    def compose(
        self,
        flow_id: UUID,
        snapshot: FlowSnapshot,
        readings: Sequence[SourceReading],
        absent: Sequence[AbsentSource],
    ) -> object:
        """The context of the agent, declaring the missing data."""
        ...


class AgentPort(Protocol):
    def decide(self, flow_id: UUID, context: object) -> object: ...


class RiskPort(Protocol):
    def check(self, flow_id: UUID, snapshot: FlowSnapshot, decisions: object) -> RiskReview: ...


class OrderPort(Protocol):
    def execute(self, flow_id: UUID, planned_at: datetime, orders: Sequence[object]) -> Sequence[object]:
        """Sends the approved orders of the cycle, closings first, and gives back their real outcomes (R1.5.5)."""
        ...


class FlowPausePort(Protocol):
    def pause_affected_by(self, flow_id: UUID, error: AutotradingError) -> None:
        """Pauses every active flow the permanent error involves, with the message of the error as reason (R1.2.4)."""
        ...


class CycleJournalPort(Protocol):
    """Describes for the record what the steps produced: only the contexts behind the steps know their data."""

    def describe(self, step: CycleStep, result: object) -> Mapping[str, object]:
        """The result of the step as JSON data; a credential never appears in it (R1.7.1)."""
        ...

    def call_cost(self, decision: object) -> CallCost | None:
        """Tokens and cost of the model call behind the decision of the agent (R1.4.6)."""
        ...


class CycleHistoryPort(Protocol):
    """Bound to the tenant of the request: it never shows the cycles of a flow of another tenant."""

    def newest(self, flow_id: UUID, offset: int, limit: int) -> list[CycleRecord]:
        """The cycles of the flow from the most recent planned instant."""
        ...

    def at(self, flow_id: UUID, planned_at: datetime) -> CycleRecord | None: ...

    def costs(self, flow_id: UUID) -> list[CycleCost]:
        """The cost of every cycle of the flow that called the model."""
        ...


class FlowDirectoryPort(Protocol):
    def exists(self, flow_id: UUID) -> bool:
        """True when the flow belongs to the tenant of the request."""
        ...
