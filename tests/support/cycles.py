"""The worker that runs the cycles, with the other contexts in memory and time compressed (ADR 0041)."""

import time
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from autotrading.adapters.outbound.threads.concurrent_calls import ThreadPoolConcurrentCallsAdapter
from autotrading.adapters.outbound.threads.planned_flows import ThreadsPlannedFlowsAdapter
from autotrading.application.flows.cycle_graph import CycleGraph, CycleSteps
from autotrading.application.flows.plan_flow_cycles import PlanFlowCyclesUseCase
from autotrading.application.flows.run_cycle import CycleGuards, RunCycleCommand, RunCycleUseCase
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.cycle_record import CycleRecord
from autotrading.domain.flows.cycle_schedule import CycleSchedule
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.cycles import (
    ACTIVE,
    PAUSED,
    TENANT,
    Failures,
    FakeAgentAdapter,
    FakeClockAdapter,
    FakeContextAdapter,
    FakeCycleEndAdapter,
    FakeCycleJournalAdapter,
    FakeCycleSchedulerAdapter,
    FakeCycleStartAdapter,
    FakeFlow,
    FakeFlowsAdapter,
    FakeOrderAdapter,
    FakeRiskAdapter,
    FakeSourcesAdapter,
    InMemoryCycleCheckpointsAdapter,
    InMemoryCycleRepositoryAdapter,
    InMemoryFlowLockAdapter,
    RecordedCycleFailuresAdapter,
)

DAY = datetime(2026, 11, 12, tzinfo=UTC)
# One second of the cycle lasts ten milliseconds of the test.
SECOND = 0.01
WAITING = 5.0
# A recorded cycle ends within milliseconds; a cycle held by the test is not awaited longer than this.
FINISHING = 0.2


def at(text: str) -> datetime:
    hours, minutes, *seconds = (int(part) for part in text.split(":"))
    return DAY.replace(hour=hours, minute=minutes, second=seconds[0] if seconds else 0)


class Cycles:
    def __init__(self) -> None:
        self.failures = Failures()
        self.clock = FakeClockAdapter(at("10:00:00"))
        self.records = InMemoryCycleRepositoryAdapter()
        self.lock = InMemoryFlowLockAdapter()
        self.flows = FakeFlowsAdapter(self.failures)
        self.sources = FakeSourcesAdapter(SECOND)
        self.context = FakeContextAdapter(self.failures)
        self.agent = FakeAgentAdapter(self.failures)
        self.risk = FakeRiskAdapter(self.failures)
        self.orders = FakeOrderAdapter(self.failures)
        self.journal = FakeCycleJournalAdapter()
        self.checkpoints = InMemoryCycleCheckpointsAdapter()
        self.failure_notices = RecordedCycleFailuresAdapter()
        self.scheduler = FakeCycleSchedulerAdapter()
        self.raised: AutotradingError | None = None
        self.planned = ThreadsPlannedFlowsAdapter()
        self.cycle_tenants: list[TenantId] = []
        self.executors = [self._executor()]

    def run_cycle(self) -> RunCycleUseCase:
        return RunCycleUseCase(
            self.graph(), CycleGuards(self.records, self.lock, self.flows, self.clock, self.failure_notices)
        )

    def graph(self) -> CycleGraph:
        steps = CycleSteps(
            FakeCycleStartAdapter(self.flows),
            self.sources,
            ThreadPoolConcurrentCallsAdapter(),
            self.context,
            self.agent,
            self.risk,
            self.orders,
            FakeCycleEndAdapter(self.flows),
            self.journal,
        )
        return CycleGraph(steps, self.records, self.checkpoints, lambda wait: wait.total_seconds() * SECOND)

    def _executor(self) -> PlanFlowCyclesUseCase:
        run_cycle = self.run_cycle()

        def run_cycle_of(tenant_id: TenantId) -> RunCycleUseCase:
            self.cycle_tenants.append(tenant_id)
            return run_cycle

        return PlanFlowCyclesUseCase(self.flows, self.planned, run_cycle_of, self.scheduler, self.clock)

    def add_executor(self) -> None:
        self.executors.append(self._executor())

    def add_flow(
        self,
        name: str,
        minutes: int = 15,
        anchor: str = "10:00:00",
        sources: tuple[str, ...] = (),
        flow_id: UUID | None = None,
        *,
        tenant_id: TenantId = TENANT,
    ) -> None:
        schedule = CycleSchedule(at(anchor), timedelta(minutes=minutes))
        flow = FakeFlow(name, schedule, sources, tenant_id=tenant_id)
        self.flows.flows[uuid4() if flow_id is None else flow_id] = flow

    def id_of(self, name: str) -> UUID:
        return next(flow_id for flow_id, flow in self.flows.flows.items() if flow.name == name)

    def flow(self, name: str) -> FakeFlow:
        return self.flows.flows[self.id_of(name)]

    def start(self, name: str, instant: str) -> None:
        flow = self.flow(name)
        flow.schedule, flow.status = CycleSchedule(at(instant), flow.schedule.interval), ACTIVE

    def pause(self, name: str) -> None:
        self.flow(name).status = PAUSED

    def set_interval(self, name: str, minutes: int) -> None:
        flow = self.flow(name)
        flow.schedule = CycleSchedule(flow.schedule.anchor, timedelta(minutes=minutes))

    def tick(self, instant: str) -> None:
        self.clock.current = at(instant)
        for executor in self.executors:
            executor.execute()

    def run_now(self, name: str) -> None:
        flow = self.flow(name)
        command = RunCycleCommand(self.id_of(name), flow.schedule, self.clock.now())
        try:
            self.run_cycle().execute(command)
        except AutotradingError as error:
            self.raised = error

    def hold(self, name: str, started: str) -> None:
        """Starts a cycle of the flow that stays in progress until the test ends."""
        self.agent.holding.add(self.id_of(name))
        self.tick(started)
        assert self.agent.entered.wait(WAITING)

    def records_of(self, name: str) -> list[CycleRecord]:
        flow_id = self.id_of(name)
        return [record for record in self.records.records if record.flow_id == flow_id]

    def last_record(self, name: str) -> CycleRecord:
        return self.records_of(name)[-1]

    def record_at(self, name: str, instant: str) -> CycleRecord:
        deadline = time.monotonic() + WAITING
        while time.monotonic() < deadline:
            found = [record for record in self.records_of(name) if record.planned_at == at(instant)]
            if found:
                # The record is written before the cycle lets go of its flow: let it finish, as minutes would.
                self.scheduler.settle(FINISHING)
                return found[0]
            time.sleep(SECOND)
        message = f"nessun ciclo registrato per {name} alle {instant}"
        raise AssertionError(message)

    def release(self) -> None:
        self.agent.released.set()
        self.sources.released.set()
