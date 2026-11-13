from collections.abc import Callable, Iterable, Mapping, Sequence
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
from autotrading.domain.tenancy.tenant_id import TenantId


@dataclass(frozen=True, slots=True)
class ScheduledFlow:
    """An active flow with the schedule that starts at its last start or resume (R1.2.1)."""

    flow_id: UUID
    schedule: CycleSchedule


@dataclass(frozen=True, slots=True)
class TenantScheduledFlow:
    """An active flow with the tenant it belongs to: the worker runs its cycle on adapters bound to that tenant."""

    tenant_id: TenantId
    flow: ScheduledFlow


@dataclass(frozen=True, slots=True)
class FlowSnapshot[S = object]:
    """The state of the flow read at the start of the cycle; the cycle only needs the names of its active sources.

    The state itself belongs to the flow and travels to the context and the risk check as it is (ADR 0041): its type
    is the one the composition root binds, never known to the cycles context (ADR 0082).
    """

    sources: tuple[str, ...]
    state: S


@dataclass(frozen=True, slots=True)
class SourceRequest[S = object]:
    """The cycle that asks its sources: the flow, its planned instant and the state read at its start.

    Every source reads the configuration of the snapshot, so a change made during the cycle waits for the next one
    (R1.1.3).
    """

    flow_id: UUID
    planned_at: datetime
    snapshot: FlowSnapshot[S]


@dataclass(frozen=True, slots=True)
class SourceReading[D = object]:
    source: str
    data: D


@dataclass(frozen=True, slots=True)
class RiskReview[O = object]:
    """The orders the risk check approved, and the outcome of every decision; the execution orders them (R1.5.5).

    The outcomes travel only to the record: approved, reduced, blocked or discarded (R1.7.1).
    """

    orders: tuple[O, ...]
    outcomes: object


class PlannedFlowsPort(Protocol):
    """The tenant and the anchor of every flow the worker planned: the ports of the cycle name only the flow."""

    def remember(self, entries: Iterable[TenantScheduledFlow]) -> None: ...

    def tenant_of(self, flow_id: UUID) -> TenantId:
        """Raises FlowOfCycleNotFoundError for a flow the worker never planned."""
        ...

    def anchor_of(self, flow_id: UUID) -> datetime:
        """Raises FlowOfCycleNotFoundError for a flow the worker never planned."""
        ...

    def tenants(self) -> set[TenantId]: ...


@dataclass(frozen=True, slots=True)
class CallAnswered[R]:
    value: R


@dataclass(frozen=True, slots=True)
class CallFailed:
    error: AutotradingError


@dataclass(frozen=True, slots=True)
class CallUnanswered:
    """The call was still running when the wait ended."""


type CallOutcome[R] = CallAnswered[R] | CallFailed | CallUnanswered


class ConcurrentCallsPort(Protocol):
    def call_all[R](self, calls: Mapping[str, Callable[[], R]], seconds: float) -> dict[str, CallOutcome[R]]:
        """Runs every call at once and waits for them only up to the seconds; a call still running is abandoned.

        A call that fails with an error of the project ends with it; any other error is raised.
        """
        ...


class ClockPort(Protocol):
    def now(self) -> datetime: ...


class ScheduledFlowsPort(Protocol):
    def active(self) -> list[ScheduledFlow]:
        """Every active flow of every tenant: the worker plans the cycles of the whole installation."""
        ...


class TenantScheduledFlowsPort(Protocol):
    def active_of_every_tenant(self) -> list[TenantScheduledFlow]:
        """Every active flow of every tenant, with the tenant it belongs to."""
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


class FlowStatePort[S = object, E = object](Protocol):
    def read(self, flow_id: UUID) -> FlowSnapshot[S]: ...

    def update(self, flow_id: UUID, executions: Sequence[E]) -> object:
        """Applies the executions of the cycle and gives back the state of the flow at the end of it."""
        ...


class SourcePort[S = object, D = object](Protocol):
    def collect(self, request: SourceRequest[S], source: str) -> D:
        """The data of one active source; any typed error makes the source absent for the cycle (R1.2.5)."""
        ...


class ContextPort[S = object, D = object, C = object](Protocol):
    def compose(
        self,
        flow_id: UUID,
        snapshot: FlowSnapshot[S],
        readings: Sequence[SourceReading[D]],
        absent: Sequence[AbsentSource],
    ) -> C:
        """The context of the agent, declaring the missing data."""
        ...


class AgentPort[C = object, A = object](Protocol):
    def decide(self, flow_id: UUID, context: C) -> A: ...


class RiskPort[S = object, A = object, O = object](Protocol):
    def check(self, flow_id: UUID, snapshot: FlowSnapshot[S], decisions: A) -> RiskReview[O]: ...


class OrderPort[O = object, E = object](Protocol):
    def execute(self, flow_id: UUID, planned_at: datetime, orders: Sequence[O]) -> Sequence[E]:
        """Sends the approved orders of the cycle, closings first, and gives back their real outcomes (R1.5.5)."""
        ...


class FlowPausePort(Protocol):
    def pause_affected_by(self, flow_id: UUID, error: AutotradingError) -> None:
        """Pauses every active flow the permanent error involves, with the message of the error as reason (R1.2.4)."""
        ...


class CycleFailureNoticePort(Protocol):
    def execute(self, flow_id: UUID, reason: str) -> None:
        """Tells the user the cycle of the flow failed, with the message of its error (R1.8.2)."""
        ...


class FlowTenantPort(Protocol):
    def tenant_of(self, flow_id: UUID) -> TenantId:
        """The tenant of a flow the worker planned."""
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


@dataclass(frozen=True, slots=True)
class FlowSummary:
    """A flow in use as the consultation shows it; the schedule is None unless the flow is active (R1.7.3)."""

    flow_id: UUID
    name: str
    account: str
    status: str
    pause_reason: str | None
    model: str
    schedule: CycleSchedule | None


class FlowSummaryPort(Protocol):
    """Bound to the tenant of the request: its flows in use, never another tenant's."""

    def in_use(self) -> list[FlowSummary]: ...


class FlowDirectoryPort(Protocol):
    def exists(self, flow_id: UUID) -> bool:
        """True when the flow belongs to the tenant of the request."""
        ...
