from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from autotrading.application.flows.errors import CycleInProgressError, FlowNotActiveError, FlowNotFoundError
from autotrading.application.flows.request_on_demand_cycle import (
    RequestOnDemandCycleCommand,
    RequestOnDemandCycleUseCase,
)
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.cycle_trigger import CycleTrigger
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.on_demand_cycles import FakeOnDemandCycleAdapter
from tests.support.flows import a_flow

TENANT = TenantId(uuid4())
NOW = datetime(2026, 11, 12, 10, 20, tzinfo=UTC)


def a_cycle(flow_id: UUID) -> CycleRecord:
    return CycleRecord(flow_id, NOW, CycleOutcome.COMPLETED, trigger=CycleTrigger.ON_DEMAND)


def test_asks_the_worker_for_a_cycle_of_an_active_flow_and_gives_it_back() -> None:
    flows = FlowStore()
    flow = a_flow(TENANT, status=FlowStatus.ACTIVE)
    flows.flows.append(flow)
    cycles = FakeOnDemandCycleAdapter(a_cycle)

    record = RequestOnDemandCycleUseCase(InMemoryFlowRepositoryAdapter(flows, TENANT), cycles).execute(
        RequestOnDemandCycleCommand(flow.id.value)
    )

    assert record == a_cycle(flow.id.value)
    assert cycles.asked == [flow.id.value]


@pytest.mark.parametrize("status", [FlowStatus.PAUSED, FlowStatus.STOPPED, FlowStatus.DRAFT])
def test_refuses_a_flow_not_active_without_asking_the_worker(status: FlowStatus) -> None:
    flows = FlowStore()
    flow = a_flow(TENANT, status=status)
    flows.flows.append(flow)
    cycles = FakeOnDemandCycleAdapter(a_cycle)

    with pytest.raises(FlowNotActiveError):
        RequestOnDemandCycleUseCase(InMemoryFlowRepositoryAdapter(flows, TENANT), cycles).execute(
            RequestOnDemandCycleCommand(flow.id.value)
        )

    assert cycles.asked == []


def test_a_flow_of_another_tenant_is_not_found_without_asking_the_worker() -> None:
    flows = FlowStore()
    other = a_flow(TenantId(uuid4()), status=FlowStatus.ACTIVE)
    flows.flows.append(other)
    cycles = FakeOnDemandCycleAdapter(a_cycle)

    with pytest.raises(FlowNotFoundError):
        RequestOnDemandCycleUseCase(InMemoryFlowRepositoryAdapter(flows, TENANT), cycles).execute(
            RequestOnDemandCycleCommand(other.id.value)
        )

    assert cycles.asked == []


def test_the_refusal_of_the_worker_reaches_the_user() -> None:
    flows = FlowStore()
    flow = a_flow(TENANT, status=FlowStatus.ACTIVE)
    flows.flows.append(flow)
    cycles = FakeOnDemandCycleAdapter(a_cycle)
    cycles.refusal = CycleInProgressError()

    with pytest.raises(CycleInProgressError):
        RequestOnDemandCycleUseCase(InMemoryFlowRepositoryAdapter(flows, TENANT), cycles).execute(
            RequestOnDemandCycleCommand(flow.id.value)
        )
