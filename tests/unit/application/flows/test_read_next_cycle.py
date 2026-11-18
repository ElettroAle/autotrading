"""When the next cycle of a flow falls, as the overview of its page shows it (R6.4.8, ADR
prossima-esecuzione-nel-riepilogo-del-flusso).
"""

from datetime import UTC, datetime, timedelta

import pytest

from autotrading.application.flows.errors import FlowNotFoundError
from autotrading.application.flows.read_next_cycle import ReadNextCycleCommand, ReadNextCycleUseCase
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter, InMemoryFlowTimingAdapter
from tests.support.flows import a_flow

STARTED = datetime(2026, 11, 18, 10, 0, tzinfo=UTC)
NOW = STARTED + timedelta(minutes=5)
TENANT = TenantId.new()


class Bench:
    def __init__(self) -> None:
        self.store = FlowStore()
        flows = InMemoryFlowRepositoryAdapter(self.store, TENANT)
        self.use_case = ReadNextCycleUseCase(flows, InMemoryFlowTimingAdapter(self.store, TENANT), lambda: NOW)

    def flow(self, status: FlowStatus, anchor: datetime | None = STARTED) -> Flow:
        flow = a_flow(TENANT, status=status)
        self.store.flows.append(flow)
        if anchor is not None:
            self.store.anchors[flow.id] = anchor
        return flow


@pytest.fixture
def bench() -> Bench:
    return Bench()


def test_an_active_flow_plans_its_next_cycle_one_interval_after_the_last_planned_one(bench: Bench) -> None:
    flow = bench.flow(FlowStatus.ACTIVE)

    assert bench.use_case.execute(ReadNextCycleCommand(flow.id)) == STARTED + timedelta(minutes=15)


@pytest.mark.parametrize("status", [FlowStatus.PAUSED, FlowStatus.STOPPED, FlowStatus.ARCHIVED])
def test_a_flow_that_is_not_active_has_no_next_cycle(bench: Bench, status: FlowStatus) -> None:
    flow = bench.flow(status)

    assert bench.use_case.execute(ReadNextCycleCommand(flow.id)) is None


def test_an_active_flow_the_database_has_not_stamped_yet_has_no_next_cycle(bench: Bench) -> None:
    flow = bench.flow(FlowStatus.ACTIVE, anchor=None)

    assert bench.use_case.execute(ReadNextCycleCommand(flow.id)) is None


def test_a_flow_of_another_tenant_is_not_found(bench: Bench) -> None:
    with pytest.raises(FlowNotFoundError):
        bench.use_case.execute(ReadNextCycleCommand(FlowId.new()))
