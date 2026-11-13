"""The ports of the cycles context in memory: the other contexts as the cycle sees them, and nothing more."""

import threading
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from autotrading.application.flows.pause_affected_flows import PauseAffectedFlowsCommand
from autotrading.application.flows.ports import (
    FlowSnapshot,
    RiskReview,
    ScheduledFlow,
    SourceReading,
    SourceRequest,
    TenantScheduledFlow,
)
from autotrading.domain.errors import AutotradingError, ErrorScope
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.cycle_record import AbsentSource, CycleRecord
from autotrading.domain.flows.cycle_schedule import CycleSchedule
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.flow_cost import CycleCost
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.flow_repository import FlowStore

ACTIVE, PAUSED = "attivo", "in pausa"
TENANT = TenantId(UUID("00000000-0000-4000-8000-000000000001"))
# A silent source or a held cycle gives up after this many real seconds: a broken cycle fails the test, never hangs it.
LONGEST_HOLD = 3.0


class FakeTransientError(AutotradingError):
    status_code = 503

    def __init__(self, message: str) -> None:
        super().__init__(message)


class FakePermanentError(AutotradingError):
    """A permanent error of an account or of a provider: the bridge pauses the flows that share it."""

    permanent = True

    def __init__(self, message: str, account: str | None = None, provider: str | None = None) -> None:
        super().__init__(message)
        self.account = account
        self.provider = provider

    @property
    def scope(self) -> ErrorScope:
        return ErrorScope(None if self.account is None else account_id_of(self.account), self.provider)


def account_id_of(name: str) -> UUID:
    """The fake flows name their account; the scope of an error names it by identifier."""
    return uuid5(NAMESPACE_URL, name)


class FakeClockAdapter:
    def __init__(self, now: datetime) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current


class InMemoryCycleRepositoryAdapter:
    def __init__(self) -> None:
        self._guard = threading.Lock()
        self._claimed: set[tuple[UUID, datetime]] = set()
        self.records: list[CycleRecord] = []

    def claim(self, flow_id: UUID, planned_at: datetime) -> bool:
        with self._guard:
            if (flow_id, planned_at) in self._claimed:
                return False
            self._claimed.add((flow_id, planned_at))
            return True

    def record(self, record: CycleRecord) -> None:
        with self._guard:
            self.records.append(record)

    def newest(self, flow_id: UUID, offset: int, limit: int) -> list[CycleRecord]:
        of_flow = sorted(
            (record for record in self.records if record.flow_id == flow_id),
            key=lambda record: record.planned_at,
            reverse=True,
        )
        return of_flow[offset : offset + limit]

    def at(self, flow_id: UUID, planned_at: datetime) -> CycleRecord | None:
        return next(
            (record for record in self.records if (record.flow_id, record.planned_at) == (flow_id, planned_at)), None
        )

    def costs(self, flow_id: UUID) -> list[CycleCost]:
        return [
            CycleCost(record.planned_at, record.cost)
            for record in self.records
            if record.flow_id == flow_id and record.cost is not None
        ]


class InMemoryCycleHistoryAdapter:
    """The cycles of every tenant, bound to one like the real adapter under row level security."""

    def __init__(self, cycles: InMemoryCycleRepositoryAdapter, flows: FlowStore, tenant_id: TenantId) -> None:
        self._cycles = cycles
        self._flows = flows
        self._tenant_id = tenant_id

    def newest(self, flow_id: UUID, offset: int, limit: int) -> list[CycleRecord]:
        return self._cycles.newest(flow_id, offset, limit) if self._owns(flow_id) else []

    def at(self, flow_id: UUID, planned_at: datetime) -> CycleRecord | None:
        return self._cycles.at(flow_id, planned_at) if self._owns(flow_id) else None

    def costs(self, flow_id: UUID) -> list[CycleCost]:
        return self._cycles.costs(flow_id) if self._owns(flow_id) else []

    def _owns(self, flow_id: UUID) -> bool:
        return any(flow.id.value == flow_id for flow in self._flows.of(self._tenant_id))


class FakeFlowDirectoryAdapter:
    def __init__(self, owned: set[UUID]) -> None:
        self.owned = owned

    def exists(self, flow_id: UUID) -> bool:
        return flow_id in self.owned


class InMemoryFlowLockAdapter:
    def __init__(self) -> None:
        self._guard = threading.Lock()
        self._locks: dict[UUID, threading.Lock] = {}

    @contextmanager
    def hold(self, flow_id: UUID) -> Iterator[bool]:
        with self._guard:
            lock = self._locks.setdefault(flow_id, threading.Lock())
        acquired = lock.acquire(blocking=False)
        try:
            yield acquired
        finally:
            if acquired:
                lock.release()


class ThreadCycleLauncherAdapter:
    """Every cycle in a thread of its own, as the worker will run them; errors are kept for the test to read."""

    def __init__(self) -> None:
        self.threads: list[threading.Thread] = []
        self.errors: list[AutotradingError] = []

    def launch(self, task: Callable[[], object]) -> None:
        thread = threading.Thread(target=self._run, args=(task,), daemon=True)
        self.threads.append(thread)
        thread.start()

    def _run(self, task: Callable[[], object]) -> None:
        try:
            task()
        except AutotradingError as error:
            self.errors.append(error)

    def settle(self, seconds: float = 1.0) -> None:
        for thread in self.threads:
            thread.join(seconds)


@dataclass
class FakeFlow:
    name: str
    schedule: CycleSchedule
    sources: tuple[str, ...] = ()
    account: str = "test-1"
    provider: str = "openrouter"
    status: str = ACTIVE
    pause_reason: str | None = None
    positions: set[str] = field(default_factory=set)
    tenant_id: TenantId = TENANT


class Failures:
    """Errors a step raises once, for one flow."""

    def __init__(self) -> None:
        self._failures: dict[tuple[UUID, CycleStep], AutotradingError] = {}

    def fail_once(self, flow_id: UUID, step: CycleStep, error: AutotradingError) -> None:
        self._failures[flow_id, step] = error

    def raise_if_failing(self, flow_id: UUID, step: CycleStep) -> None:
        error = self._failures.pop((flow_id, step), None)
        if error is not None:
            raise error


class FakeCycleStartAdapter:
    def __init__(self, flows: FakeFlowsAdapter) -> None:
        self._flows = flows

    def execute(self, flow_id: UUID, anchor: datetime) -> FlowSnapshot:
        return self._flows.read(flow_id, anchor)


class FakeCycleEndAdapter:
    def __init__(self, flows: FakeFlowsAdapter) -> None:
        self._flows = flows

    def execute(self, flow_id: UUID, anchor: datetime, executions: Sequence[object]) -> object:
        return self._flows.update(flow_id, anchor, executions)


class FakeFlowsAdapter:
    """The flows context as the cycle sees it: schedules, state, pause."""

    def __init__(self, failures: Failures) -> None:
        self.flows: dict[UUID, FakeFlow] = {}
        self.updates: list[tuple[UUID, Sequence[object]]] = []
        self._failures = failures

    def active_of_every_tenant(self) -> list[TenantScheduledFlow]:
        return [
            TenantScheduledFlow(flow.tenant_id, ScheduledFlow(flow_id, flow.schedule))
            for flow_id, flow in self.flows.items()
            if flow.status == ACTIVE
        ]

    def read(self, flow_id: UUID, anchor: datetime) -> FlowSnapshot:  # noqa: ARG002 - the signature of the port
        self._failures.raise_if_failing(flow_id, CycleStep.READ_FLOW_STATE)
        flow = self.flows[flow_id]
        return FlowSnapshot(flow.sources, {"flow": flow.name, "positions": sorted(flow.positions)})

    def update(
        self,
        flow_id: UUID,
        anchor: datetime,  # noqa: ARG002 - the signature of the port
        executions: Sequence[object],
    ) -> object:
        self._failures.raise_if_failing(flow_id, CycleStep.UPDATE_FLOW_STATE)
        self.updates.append((flow_id, executions))
        return {"flow": self.flows[flow_id].name, "executions": len(executions)}

    def execute(self, command: PauseAffectedFlowsCommand) -> None:
        failing = self.flows[command.flow_id]
        for flow in self.flows.values():
            involved = (
                flow is failing
                or account_id_of(flow.account) == command.account_id
                or flow.provider == command.provider
            )
            if involved and flow.status == ACTIVE:
                flow.status, flow.pause_reason = PAUSED, command.reason


class FakeSourcesAdapter:
    """Sources that answer at once, fail, answer late or never answer until the test ends."""

    def __init__(self, seconds: float) -> None:
        self._seconds = seconds
        self.silent: set[str] = set()
        self.late: dict[str, float] = {}
        self.failing: dict[str, AutotradingError] = {}
        self.released = threading.Event()

    def collect(self, request: SourceRequest, source: str) -> object:
        flow_id = request.flow_id
        if source in self.silent:
            self.released.wait(LONGEST_HOLD)
        if source in self.late:
            time.sleep(self.late[source] * self._seconds)
        error = self.failing.get(source)
        if error is not None:
            raise error
        return {"source": source, "flow_id": str(flow_id)}


@dataclass(frozen=True, slots=True)
class ComposedContext:
    snapshot: FlowSnapshot
    readings: tuple[SourceReading, ...]
    absent: tuple[AbsentSource, ...]


class FakeContextAdapter:
    def __init__(self, failures: Failures) -> None:
        self.composed: dict[UUID, ComposedContext] = {}
        self._failures = failures

    def compose(
        self, flow_id: UUID, snapshot: FlowSnapshot, readings: Sequence[SourceReading], absent: Sequence[AbsentSource]
    ) -> object:
        self._failures.raise_if_failing(flow_id, CycleStep.COMPOSE_CONTEXT)
        context = ComposedContext(snapshot, tuple(readings), tuple(absent))
        self.composed[flow_id] = context
        return context


class FakeAgentAdapter:
    """Decides the assets to open; it can hold a cycle until the test releases it."""

    def __init__(self, failures: Failures) -> None:
        self.decisions: dict[UUID, list[str]] = {}
        self.calls: list[UUID] = []
        self.contexts: list[object] = []
        self.holding: set[UUID] = set()
        self.entered = threading.Event()
        self.released = threading.Event()
        self._failures = failures

    def decide(self, flow_id: UUID, context: object) -> object:
        self.calls.append(flow_id)
        self.contexts.append(context)
        if flow_id in self.holding:
            self.entered.set()
            self.released.wait(LONGEST_HOLD)
        self._failures.raise_if_failing(flow_id, CycleStep.AGENT_DECISION)
        return list(self.decisions.get(flow_id, []))


class FakeRiskAdapter:
    """Approves every decision as an order."""

    def __init__(self, failures: Failures) -> None:
        self.snapshots: list[FlowSnapshot] = []
        self._failures = failures

    def check(self, flow_id: UUID, snapshot: FlowSnapshot, decisions: object) -> RiskReview:
        self._failures.raise_if_failing(flow_id, CycleStep.RISK_CHECK)
        self.snapshots.append(snapshot)
        assert isinstance(decisions, list)
        return RiskReview(tuple(decisions), {asset: "approvata" for asset in decisions})


class FakeOrderAdapter:
    def __init__(self, failures: Failures) -> None:
        self.sent: list[tuple[UUID, datetime, object]] = []
        self.unanswered: set[str] = set()
        self._failures = failures

    def execute(self, flow_id: UUID, planned_at: datetime, orders: Sequence[object]) -> Sequence[object]:
        self._failures.raise_if_failing(flow_id, CycleStep.ORDER_EXECUTION)
        return [self._executed(flow_id, planned_at, order) for order in orders]

    def _executed(self, flow_id: UUID, planned_at: datetime, order: object) -> object:
        if order in self.unanswered:
            message = f"l'exchange non risponde all'ordine su {order}"
            raise FakeTransientError(message)
        self.sent.append((flow_id, planned_at, order))
        return {"order": order, "filled": True}


class FakeCycleJournalAdapter:
    """Describes every result as text: what the real journal does per type, the fake does with its representation."""

    def __init__(self) -> None:
        self.cost: CallCost | None = CallCost(1000, 200, Decimal("0.002"))

    def describe(self, step: CycleStep, result: object) -> dict[str, object]:
        return {"step": step.value, "result": repr(result)}

    def call_cost(self, decision: object) -> CallCost | None:  # noqa: ARG002 - the same cost for every call
        return self.cost


class RecordedCycleFailuresAdapter:
    """The failed cycles told to the user, flow and reason."""

    def __init__(self) -> None:
        self.told: list[tuple[UUID, str]] = []

    def execute(self, flow_id: UUID, reason: str) -> None:
        self.told.append((flow_id, reason))
