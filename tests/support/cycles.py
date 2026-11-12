"""The worker that runs the cycles, with the other contexts in memory and time compressed (ADR 0041)."""

import time
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from autotrading.application.cycles.run_cycle import CycleGuards, CycleSteps, RunCycleCommand, RunCycleUseCase
from autotrading.application.cycles.run_due_cycles import RunDueCyclesUseCase
from autotrading.application.cycles.source_collector import SourceCollector
from autotrading.domain.cycles.cycle_record import CycleRecord
from autotrading.domain.cycles.cycle_schedule import CycleSchedule
from autotrading.domain.errors import AutotradingError
from tests.fakes.cycles import (
    ACTIVE,
    PAUSED,
    Failures,
    FakeAgentAdapter,
    FakeClockAdapter,
    FakeContextAdapter,
    FakeCycleJournalAdapter,
    FakeFlow,
    FakeFlowsAdapter,
    FakeOrderAdapter,
    FakeRiskAdapter,
    FakeSourcesAdapter,
    InMemoryCycleRepositoryAdapter,
    InMemoryFlowLockAdapter,
    ThreadCycleLauncherAdapter,
)

DAY = datetime(2026, 11, 12, tzinfo=UTC)
# One second of the cycle lasts ten milliseconds of the test.
SECOND = 0.01
WAITING = 5.0


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
        self.launcher = ThreadCycleLauncherAdapter()
        self.raised: AutotradingError | None = None
        self.executors = [self._executor()]

    def run_cycle(self) -> RunCycleUseCase:
        collector = SourceCollector(self.sources, lambda wait: wait.total_seconds() * SECOND)
        steps = CycleSteps(self.flows, collector, self.context, self.agent, self.risk, self.orders, self.journal)
        return RunCycleUseCase(steps, CycleGuards(self.records, self.lock, self.flows, self.clock))

    def _executor(self) -> RunDueCyclesUseCase:
        return RunDueCyclesUseCase(self.flows, self.run_cycle(), self.launcher, self.clock)

    def add_executor(self) -> None:
        self.executors.append(self._executor())

    def add_flow(
        self,
        name: str,
        minutes: int = 15,
        anchor: str = "10:00:00",
        sources: tuple[str, ...] = (),
        flow_id: UUID | None = None,
    ) -> None:
        schedule = CycleSchedule(at(anchor), timedelta(minutes=minutes))
        self.flows.flows[uuid4() if flow_id is None else flow_id] = FakeFlow(name, schedule, sources)

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
                return found[0]
            time.sleep(SECOND)
        message = f"nessun ciclo registrato per {name} alle {instant}"
        raise AssertionError(message)

    def release(self) -> None:
        self.agent.released.set()
        self.sources.released.set()
