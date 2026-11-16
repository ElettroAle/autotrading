from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from autotrading.application.flows.pause_affected_flows import PauseAffectedFlowsCommand
from autotrading.application.flows.pause_after_consecutive_failures import PauseAfterConsecutiveFailuresUseCase
from autotrading.domain.flows.cycle_record import CycleFailure, CycleOutcome, CycleRecord
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.consecutive_failures import InMemoryConsecutiveFailuresAdapter
from tests.fakes.cycles import FakeTransientError, InMemoryCycleRepositoryAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId.new()
ANCHOR = datetime(2026, 11, 12, 10, tzinfo=UTC)
ERROR = FakeTransientError("timeout del modello")
REASON = "cicli falliti consecutivi: timeout del modello"


class World:
    """A flow with its recorded cycles, and the pauses asked for it."""

    def __init__(self, maximum: int | None) -> None:
        self.store = FlowStore()
        self.cycles = InMemoryCycleRepositoryAdapter()
        configuration = replace(a_configuration(), max_consecutive_failures=maximum)
        self.flow: Flow = a_flow(TENANT, status=FlowStatus.ACTIVE, configuration=configuration)
        self.store.flows.append(self.flow)
        self.store.anchors[self.flow.id] = ANCHOR
        self.paused: list[PauseAffectedFlowsCommand] = []
        failures = InMemoryConsecutiveFailuresAdapter(self.cycles, self.store)
        self.use_case = PauseAfterConsecutiveFailuresUseCase(
            InMemoryFlowRepositoryAdapter(self.store, TENANT), failures, self
        )

    @property
    def flow_id(self) -> UUID:
        return self.flow.id.value

    def execute(self, command: PauseAffectedFlowsCommand) -> None:
        self.paused.append(command)

    def failed(self, count: int) -> None:
        for _ in range(count):
            failure = CycleFailure(CycleStep.AGENT_DECISION, type(ERROR).__name__, str(ERROR))
            self.cycles.record(CycleRecord(self.flow_id, self._next(), CycleOutcome.FAILED, failure=failure))

    def completed(self) -> None:
        self.cycles.record(CycleRecord(self.flow_id, self._next(), CycleOutcome.COMPLETED))

    def _next(self) -> datetime:
        return ANCHOR + timedelta(minutes=15) * len(self.cycles.records)


def test_the_flow_is_paused_when_its_failed_cycles_in_a_row_reach_the_maximum() -> None:
    world = World(maximum=3)
    world.failed(3)

    paused = world.use_case.execute(world.flow_id, ERROR)

    assert paused is True
    assert world.paused == [PauseAffectedFlowsCommand(world.flow_id, f"3 {REASON}")]


def test_the_flow_keeps_running_below_the_maximum() -> None:
    world = World(maximum=3)
    world.failed(2)

    assert world.use_case.execute(world.flow_id, ERROR) is False
    assert world.paused == []


def test_a_flow_without_maximum_keeps_running_whatever_its_failures() -> None:
    world = World(maximum=None)
    world.failed(10)

    assert world.use_case.execute(world.flow_id, ERROR) is False
    assert world.paused == []


def test_a_completed_cycle_starts_the_count_again() -> None:
    world = World(maximum=3)
    world.failed(2)
    world.completed()
    world.failed(2)

    assert world.use_case.execute(world.flow_id, ERROR) is False


@pytest.mark.parametrize("maximum", [1, 2])
def test_the_reason_counts_the_failed_cycles_in_a_row(maximum: int) -> None:
    world = World(maximum=maximum)
    world.failed(4)

    world.use_case.execute(world.flow_id, ERROR)

    assert world.paused == [PauseAffectedFlowsCommand(world.flow_id, f"4 {REASON}")]
