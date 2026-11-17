from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from autotrading.application.flows.errors import CycleInProgressError, FlowNotActiveError, FlowNotFoundError
from autotrading.application.flows.run_cycle import RunCycleCommand
from autotrading.application.flows.run_cycle_on_demand import RunCycleOnDemandCommand, RunCycleOnDemandUseCase
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.cycle_schedule import CycleSchedule
from autotrading.domain.flows.cycle_trigger import CycleTrigger
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.cycles import FakeClockAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter, InMemoryFlowTimingAdapter
from tests.support.flows import a_flow

TENANT = TenantId(uuid4())
ANCHOR = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
NOW = datetime(2026, 11, 12, 10, 20, 7, tzinfo=UTC)


class RecordedRuns:
    """The cycle the worker runs, as the planned ones: what it was asked and what it gives back."""

    def __init__(self) -> None:
        self.commands: list[RunCycleCommand] = []
        self.taken = False

    def run(self, command: RunCycleCommand) -> CycleRecord | None:
        self.commands.append(command)
        if self.taken:
            return None
        return CycleRecord(command.flow_id, command.planned_at, CycleOutcome.COMPLETED, trigger=command.trigger)


def world(status: FlowStatus = FlowStatus.ACTIVE, anchor: datetime | None = ANCHOR) -> tuple[Flow, FlowStore]:
    flows = FlowStore()
    flow = a_flow(TENANT, status=status)
    flows.flows.append(flow)
    if anchor is not None:
        flows.anchors[flow.id] = anchor
    return flow, flows


def use_case(flows: FlowStore, runs: RecordedRuns) -> RunCycleOnDemandUseCase:
    return RunCycleOnDemandUseCase(
        InMemoryFlowRepositoryAdapter(flows, TENANT),
        InMemoryFlowTimingAdapter(flows, TENANT),
        FakeClockAdapter(NOW),
        runs.run,
    )


def test_runs_the_cycle_of_the_flow_now_on_its_schedule_as_asked_by_the_user() -> None:
    flow, flows = world()
    runs = RecordedRuns()

    record = use_case(flows, runs).execute(RunCycleOnDemandCommand(flow.id.value))

    interval = timedelta(minutes=flow.configuration.cycle_interval.minutes)
    assert runs.commands == [
        RunCycleCommand(flow.id.value, CycleSchedule(ANCHOR, interval), NOW, CycleTrigger.ON_DEMAND)
    ]
    assert (record.flow_id, record.planned_at, record.trigger) == (flow.id.value, NOW, CycleTrigger.ON_DEMAND)


@pytest.mark.parametrize("status", [FlowStatus.PAUSED, FlowStatus.STOPPED, FlowStatus.DRAFT])
def test_refuses_a_flow_that_runs_no_cycles(status: FlowStatus) -> None:
    flow, flows = world(status)
    runs = RecordedRuns()

    with pytest.raises(FlowNotActiveError):
        use_case(flows, runs).execute(RunCycleOnDemandCommand(flow.id.value))

    assert runs.commands == []


def test_refuses_an_active_flow_the_database_has_not_anchored_yet() -> None:
    flow, flows = world(anchor=None)
    runs = RecordedRuns()

    with pytest.raises(FlowNotActiveError):
        use_case(flows, runs).execute(RunCycleOnDemandCommand(flow.id.value))

    assert runs.commands == []


def test_a_flow_of_another_tenant_is_not_found() -> None:
    _, flows = world()
    other = a_flow(TenantId(uuid4()), status=FlowStatus.ACTIVE)
    flows.flows.append(other)

    with pytest.raises(FlowNotFoundError):
        use_case(flows, RecordedRuns()).execute(RunCycleOnDemandCommand(other.id.value))


def test_an_instant_another_executor_already_took_is_a_cycle_in_progress() -> None:
    flow, flows = world()
    runs = RecordedRuns()
    runs.taken = True

    with pytest.raises(CycleInProgressError):
        use_case(flows, runs).execute(RunCycleOnDemandCommand(flow.id.value))
