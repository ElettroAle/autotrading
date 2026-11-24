"""The ports of the cycles context in memory: the other contexts as the cycle sees them, and nothing more."""

import threading
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from autotrading.application.flows.pause_affected_flows import PauseAffectedFlowsCommand
from autotrading.application.flows.pause_flows_on_expired_keys import PauseFlowsOnExpiredKeysCommand
from autotrading.application.flows.ports import (
    CycleJob,
    FailedModelCall,
    FlowSnapshot,
    ReversedExecutions,
    RiskReview,
    ScheduledFlow,
    SourceReading,
    SourceRequest,
    TenantScheduledFlow,
)
from autotrading.domain.errors import AutotradingError, ErrorScope
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.cycle_filter import CycleFilter
from autotrading.domain.flows.cycle_record import AbsentSource, CycleOutcome, CycleRecord, FailedAttempt
from autotrading.domain.flows.cycle_schedule import CycleSchedule
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.decision_filter import DecisionFilter
from autotrading.domain.flows.flow_cost import CycleCost
from autotrading.domain.flows.recorded_decision import DatedDecision, DecidedCycle, DecisionAction, RecordedDecision
from autotrading.domain.flows.selections import ActiveSource
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.flow_repository import FlowStore
from tests.support.source_selections import adapter_of

ACTIVE, PAUSED = "attivo", "in pausa"
TENANT = TenantId(UUID("00000000-0000-4000-8000-000000000001"))
# A silent source or a held cycle gives up after this many real seconds: a broken cycle fails the test, never hangs it.
LONGEST_HOLD = 3.0
FAKE_CONFIDENCE = 70


class FakeTransientError(AutotradingError):
    status_code = 503

    def __init__(self, message: str) -> None:
        super().__init__(message)


class FakePermanentError(AutotradingError):
    """A permanent error of an account or of a provider: the bridge pauses the flows that share it."""

    declared_permanent = True

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
    """Stands still, unless the test makes every reading a step later than the one before, as time passes during a
    call it measures (R6.3.1)."""

    def __init__(self, now: datetime, step: timedelta = timedelta(0)) -> None:
        self.current = now
        self.step = step

    def now(self) -> datetime:
        current = self.current
        self.current += self.step
        return current


class InMemoryCycleRepositoryAdapter:
    def __init__(self) -> None:
        self._guard = threading.Lock()
        self._claimed: set[tuple[UUID, datetime]] = set()
        self.records: list[CycleRecord] = []
        # An error the next record raises once, as a database out of reach would.
        self.failing_once: AutotradingError | None = None

    def claim(self, flow_id: UUID, planned_at: datetime) -> bool:
        with self._guard:
            if (flow_id, planned_at) in self._claimed:
                return False
            self._claimed.add((flow_id, planned_at))
            return True

    def record(self, record: CycleRecord) -> None:
        error, self.failing_once = self.failing_once, None
        if error is not None:
            raise error
        with self._guard:
            self.records.append(record)

    def newest(self, flow_id: UUID, offset: int, limit: int) -> list[CycleRecord]:
        of_flow = sorted(
            (record for record in self.records if record.flow_id == flow_id),
            key=lambda record: record.planned_at,
            reverse=True,
        )
        return of_flow[offset : offset + limit]

    def failed_within(self, flow_id: UUID, window: TimeWindow) -> int:
        return sum(
            1
            for record in self.records
            if record.flow_id == flow_id
            and record.outcome is CycleOutcome.FAILED
            and window.contains(record.planned_at)
        )

    def matching(self, flow_id: UUID, criteria: CycleFilter, offset: int, limit: int) -> list[CycleRecord]:
        matched = [record for record in self.newest(flow_id, 0, len(self.records)) if _matches(record, criteria)]
        return matched[offset : offset + limit]

    def count(self, flow_id: UUID, criteria: CycleFilter) -> int:
        return len(self.matching(flow_id, criteria, 0, len(self.records)))

    def at(self, flow_id: UUID, planned_at: datetime) -> CycleRecord | None:
        return next(
            (record for record in self.records if (record.flow_id, record.planned_at) == (flow_id, planned_at)), None
        )

    def costs(self, flow_id: UUID) -> list[CycleCost]:
        return [
            CycleCost(record.planned_at, record.cost)
            for record in self.records
            if record.flow_id == flow_id and record.model_called
        ]

    def costs_within(self, flow_id: UUID, window: TimeWindow) -> list[CycleCost]:
        return [cost for cost in self.costs(flow_id) if window.contains(cost.planned_at)]

    def last_decided(self, flow_id: UUID) -> DecidedCycle | None:
        decided = (
            record
            for record in self.newest(flow_id, 0, len(self.records))
            if record.outcome is CycleOutcome.COMPLETED and record.decisions
        )
        latest = next(decided, None)
        return None if latest is None else DecidedCycle(latest.planned_at, latest.decisions)

    def decisions_matching(
        self, flow_id: UUID, criteria: DecisionFilter, window: TimeWindow, offset: int, limit: int
    ) -> list[DatedDecision]:
        matched = [
            DatedDecision(record.planned_at, decision)
            for record in self.newest(flow_id, 0, len(self.records))
            if record.outcome is CycleOutcome.COMPLETED and window.contains(record.planned_at)
            for decision in sorted(record.decisions, key=lambda decision: decision.asset)
            if criteria.matches(decision)
        ]
        return matched[offset : offset + limit]

    def decisions_count(self, flow_id: UUID, criteria: DecisionFilter, window: TimeWindow) -> int:
        every = sum(len(record.decisions) for record in self.records)
        return len(self.decisions_matching(flow_id, criteria, window, 0, every))


class InMemoryCycleHistoryAdapter:
    """The cycles of every tenant, bound to one like the real adapter under row level security."""

    def __init__(self, cycles: InMemoryCycleRepositoryAdapter, flows: FlowStore, tenant_id: TenantId) -> None:
        self._cycles = cycles
        self._flows = flows
        self._tenant_id = tenant_id

    def newest(self, flow_id: UUID, offset: int, limit: int) -> list[CycleRecord]:
        return self._cycles.newest(flow_id, offset, limit) if self._owns(flow_id) else []

    def failed_within(self, flow_id: UUID, window: TimeWindow) -> int:
        return self._cycles.failed_within(flow_id, window) if self._owns(flow_id) else 0

    def matching(self, flow_id: UUID, criteria: CycleFilter, offset: int, limit: int) -> list[CycleRecord]:
        return self._cycles.matching(flow_id, criteria, offset, limit) if self._owns(flow_id) else []

    def count(self, flow_id: UUID, criteria: CycleFilter) -> int:
        return self._cycles.count(flow_id, criteria) if self._owns(flow_id) else 0

    def at(self, flow_id: UUID, planned_at: datetime) -> CycleRecord | None:
        return self._cycles.at(flow_id, planned_at) if self._owns(flow_id) else None

    def costs(self, flow_id: UUID) -> list[CycleCost]:
        return self._cycles.costs(flow_id) if self._owns(flow_id) else []

    def costs_within(self, flow_id: UUID, window: TimeWindow) -> list[CycleCost]:
        return self._cycles.costs_within(flow_id, window) if self._owns(flow_id) else []

    def last_decided(self, flow_id: UUID) -> DecidedCycle | None:
        return self._cycles.last_decided(flow_id) if self._owns(flow_id) else None

    def decisions_matching(
        self, flow_id: UUID, criteria: DecisionFilter, window: TimeWindow, offset: int, limit: int
    ) -> list[DatedDecision]:
        return self._cycles.decisions_matching(flow_id, criteria, window, offset, limit) if self._owns(flow_id) else []

    def decisions_count(self, flow_id: UUID, criteria: DecisionFilter, window: TimeWindow) -> int:
        return self._cycles.decisions_count(flow_id, criteria, window) if self._owns(flow_id) else 0

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


class FakeCycleSchedulerAdapter:
    """Runs every job it keeps at once, each in a thread of its own, as the scheduler does at the instant of the tick.

    The tests tick only at planned instants or check that nothing new runs: a job run again takes no instant twice.
    Errors are kept for the test to read.
    """

    def __init__(self) -> None:
        self.threads: list[threading.Thread] = []
        self.errors: list[AutotradingError] = []
        self.kept: list[CycleJob] = []

    def keep(self, jobs: Sequence[CycleJob]) -> None:
        self.kept = list(jobs)
        for job in jobs:
            thread = threading.Thread(target=self._run, args=(job.run,), daemon=True)
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
    """Errors a step raises for one flow: once, a number of times in a row, or at every call."""

    def __init__(self) -> None:
        self._failures: dict[tuple[UUID, CycleStep], list[AutotradingError]] = {}
        self._always: dict[tuple[UUID, CycleStep], AutotradingError] = {}

    def fail_once(self, flow_id: UUID, step: CycleStep, error: AutotradingError) -> None:
        self.fail(flow_id, step, error, times=1)

    def fail(self, flow_id: UUID, step: CycleStep, error: AutotradingError, *, times: int) -> None:
        self._failures[flow_id, step] = [error] * times

    def fail_always(self, flow_id: UUID, step: CycleStep, error: AutotradingError) -> None:
        self._always[flow_id, step] = error

    def raise_if_failing(self, flow_id: UUID, step: CycleStep) -> None:
        always = self._always.get((flow_id, step))
        if always is not None:
            raise always
        pending = self._failures.get((flow_id, step), [])
        if pending:
            raise pending.pop(0)


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


class FakeFlowActivityAdapter:
    """Whether a flow runs cycles, from its status in the fake flows."""

    def __init__(self, flows: FakeFlowsAdapter) -> None:
        self._flows = flows

    def execute(self, flow_id: UUID) -> bool:
        return self._flows.flows[flow_id].status == ACTIVE


class FakeExpiredKeysAdapter:
    """No key of the flows has expired, unless a test names the flows whose key has: those it pauses (R6.2.2)."""

    def __init__(self, flows: FakeFlowsAdapter) -> None:
        self._flows = flows
        self.expired_for: dict[UUID, str] = {}

    def execute(self, command: PauseFlowsOnExpiredKeysCommand) -> bool:
        flow_id = command.flow_id
        reason = None if flow_id is None else self.expired_for.get(flow_id)
        if flow_id is None or reason is None:
            return False
        flow = self._flows.flows[flow_id]
        flow.status, flow.pause_reason = PAUSED, reason
        return True


class FakeFlowsAdapter:
    """The flows context as the cycle sees it: schedules, state, pause."""

    def __init__(self, failures: Failures) -> None:
        self.flows: dict[UUID, FakeFlow] = {}
        self.updates: list[tuple[UUID, Sequence[object]]] = []
        self.reads: list[UUID] = []
        self._failures = failures

    def active_of_every_tenant(self) -> list[TenantScheduledFlow]:
        return [
            TenantScheduledFlow(flow.tenant_id, ScheduledFlow(flow_id, flow.schedule))
            for flow_id, flow in self.flows.items()
            if flow.status == ACTIVE
        ]

    def read(self, flow_id: UUID, anchor: datetime) -> FlowSnapshot:  # noqa: ARG002 - the signature of the port
        self.reads.append(flow_id)
        self._failures.raise_if_failing(flow_id, CycleStep.READ_FLOW_STATE)
        flow = self.flows[flow_id]
        sources = tuple(ActiveSource(source, adapter_of(source)) for source in flow.sources)
        return FlowSnapshot(sources, {"flow": flow.name, "positions": sorted(flow.positions)})

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
        failing = None if command.flow_id is None else self.flows[command.flow_id]
        for flow in self.flows.values():
            involved = (
                flow is failing
                or account_id_of(flow.account) == command.account_id
                or flow.provider == command.provider
            )
            if involved and flow.status == ACTIVE:
                flow.status, flow.pause_reason = PAUSED, command.reason


class FakeSourcesAdapter:
    """Sources that answer at once, fail, answer late or never answer until the test ends.

    It counts the sources asked at the same time: the most at once tells whether they were asked in parallel.
    """

    def __init__(self, seconds: float) -> None:
        self._seconds = seconds
        self.silent: set[str] = set()
        self.late: dict[str, float] = {}
        self.failing: dict[str, AutotradingError] = {}
        self.released = threading.Event()
        self._asking = 0
        self.most_at_once = 0
        self._counting = threading.Lock()

    def execute(self, request: SourceRequest, active: ActiveSource) -> object:
        with self._counting:
            self._asking += 1
            self.most_at_once = max(self.most_at_once, self._asking)
        try:
            return self._answer(request, active)
        finally:
            with self._counting:
                self._asking -= 1

    def _answer(self, request: SourceRequest, active: ActiveSource) -> object:
        flow_id = request.flow_id
        source = active.source
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

    def execute(
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

    def execute(self, flow_id: UUID, context: object) -> object:
        self.calls.append(flow_id)
        self.contexts.append(context)
        if flow_id in self.holding:
            self.entered.set()
            self.released.wait(LONGEST_HOLD)
        self._failures.raise_if_failing(flow_id, CycleStep.AGENT_DECISION)
        return list(self.decisions.get(flow_id, []))


class FakeRiskAdapter:
    """Approves every decision as an order; reversing, it leaves the opening of a reversal waiting among them."""

    def __init__(self, failures: Failures) -> None:
        self.snapshots: list[FlowSnapshot] = []
        self.reversing = False
        self._failures = failures

    def execute(self, flow_id: UUID, snapshot: FlowSnapshot, decisions: object) -> RiskReview:
        self._failures.raise_if_failing(flow_id, CycleStep.RISK_CHECK)
        self.snapshots.append(snapshot)
        assert isinstance(decisions, list)
        return RiskReview(tuple(decisions), {asset: "approvata" for asset in decisions}, reversing=self.reversing)


class FakeReversalAdapter:
    """Opens again every order it is given, once the orders of the cycle are sent; or fails, once, with its error."""

    def __init__(self) -> None:
        self.calls: list[tuple[UUID, datetime, datetime, tuple[object, ...]]] = []
        self.failing: AutotradingError | None = None
        # The attempts the reversal tells it retried before its readings went through.
        self.failed_attempts: tuple[FailedAttempt, ...] = ()

    def execute(
        self, flow_id: UUID, planned_at: datetime, anchor: datetime, orders: Sequence[object]
    ) -> ReversedExecutions:
        failing, self.failing = self.failing, None
        if failing is not None:
            raise failing
        self.calls.append((flow_id, planned_at, anchor, tuple(orders)))
        return ReversedExecutions(
            tuple({"reopened": order} for order in orders),
            {order: "riaperta" for order in orders},
            self.failed_attempts,
        )


class FakeOrderAdapter:
    def __init__(self, failures: Failures) -> None:
        self.sent: list[tuple[UUID, datetime, object]] = []
        self.unanswered: set[str] = set()
        # The attempts the orders context tells it retried, among the executions as the real one gives them.
        self.failed_attempts: tuple[FailedAttempt, ...] = ()
        self._failures = failures

    def execute(self, flow_id: UUID, planned_at: datetime, orders: Sequence[object]) -> Sequence[object]:
        self._failures.raise_if_failing(flow_id, CycleStep.ORDER_EXECUTION)
        return [*(self._executed(flow_id, planned_at, order) for order in orders), *self.failed_attempts]

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
        self.attempts: int | None = 1
        self.failed: FailedModelCall | None = None
        self.failures: list[AutotradingError] = []

    def describe(self, step: CycleStep, result: object) -> dict[str, object]:
        return {"step": step.value, "result": repr(result)}

    def call_cost(self, decision: object) -> CallCost | None:  # noqa: ARG002 - the same cost for every call
        return self.cost

    def call_attempts(self, decision: object) -> int | None:  # noqa: ARG002 - the same attempts for every call
        return self.attempts

    def failed_call(self, error: AutotradingError) -> FailedModelCall | None:
        """The same failed call for every error, keeping the errors it was asked about."""
        self.failures.append(error)
        return self.failed

    def failed_attempts(self, step: CycleStep, result: object) -> tuple[FailedAttempt, ...]:  # noqa: ARG002
        """The failed attempts the fake orders put among their executions, as they are."""
        items = result if isinstance(result, list | tuple) else ()
        return tuple(item for item in items if isinstance(item, FailedAttempt))

    def recorded_decisions(self, decision: object) -> tuple[RecordedDecision, ...]:
        """Every asset the fake agent decided is a long opening, with the confidence of the fake."""
        assets = decision if isinstance(decision, list) else []
        return tuple(
            RecordedDecision(asset, DecisionAction.OPEN, TradeSide.LONG, FAKE_CONFIDENCE, f"apertura di {asset}")
            for asset in assets
        )


class InMemoryCycleEquityAdapter:
    """The equity every cycle recorded: the flow, the planned instant and the state it was taken from."""

    def __init__(self) -> None:
        self.recorded: list[tuple[UUID, datetime, object]] = []

    def execute(self, flow_id: UUID, planned_at: datetime, state: object) -> None:
        self.recorded.append((flow_id, planned_at, state))


class RecordedCycleFailuresAdapter:
    """The failed cycles told to the user, flow and reason."""

    def __init__(self) -> None:
        self.told: list[tuple[UUID, str]] = []

    def execute(self, flow_id: UUID, reason: str) -> None:
        self.told.append((flow_id, reason))


class RecordedConsecutiveFailurePausesAdapter:
    """The failed cycles that asked for the pause after consecutive failures, with the failures told by then."""

    def __init__(self, notices: RecordedCycleFailuresAdapter) -> None:
        self.asked: list[tuple[UUID, AutotradingError]] = []
        self.told_before: list[list[tuple[UUID, str]]] = []
        self._notices = notices

    def execute(self, flow_id: UUID, error: AutotradingError) -> None:
        self.asked.append((flow_id, error))
        self.told_before.append(list(self._notices.told))


class InMemoryCycleCheckpointsAdapter:
    """The checkpoints of the cycles kept in memory, serialized as the checkpointer in PostgreSQL serializes them."""

    def __init__(self) -> None:
        self.saver = InMemorySaver()

    def thread(self, flow_id: UUID, planned_at: datetime) -> str:
        return f"{flow_id}/{planned_at.isoformat()}"

    @contextmanager
    def opened(self) -> Iterator[BaseCheckpointSaver[str]]:
        yield self.saver


def _matches(record: CycleRecord, criteria: CycleFilter) -> bool:
    return (
        (criteria.outcome is None or record.outcome is criteria.outcome)
        and (criteria.decision is None or criteria.decision.taken_in(record.decisions))
        and criteria.window.contains(record.planned_at)
    )
