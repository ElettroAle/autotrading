import pytest

from autotrading.application.flows.errors import FlowNotFoundError
from autotrading.application.flows.get_flow import GetFlowCommand, GetFlowUseCase
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.support.flows import a_flow


def test_an_archived_flow_is_read_with_its_status() -> None:
    store = FlowStore()
    tenant_id = TenantId.new()
    repository = InMemoryFlowRepositoryAdapter(store, tenant_id)
    flow = a_flow(tenant_id, status=FlowStatus.ARCHIVED)
    repository.add(flow)

    read = GetFlowUseCase(repository).execute(GetFlowCommand(flow.id))

    assert (read.id, read.status) == (flow.id, FlowStatus.ARCHIVED)


def test_a_flow_of_another_tenant_or_missing_is_not_found() -> None:
    store = FlowStore()
    anna = TenantId.new()
    flow = a_flow(anna, status=FlowStatus.ARCHIVED)
    InMemoryFlowRepositoryAdapter(store, anna).add(flow)
    bruno_flows = InMemoryFlowRepositoryAdapter(store, TenantId.new())

    for flow_id in (flow.id, FlowId.new()):
        with pytest.raises(FlowNotFoundError):
            GetFlowUseCase(bruno_flows).execute(GetFlowCommand(flow_id))
