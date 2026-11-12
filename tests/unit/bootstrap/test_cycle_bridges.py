"""The bridge bootstrap builds from the flows context to the cycles context (ADR 0046)."""

from uuid import uuid4

from autotrading.bootstrap import FlowDirectoryFromFlows
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.support.flows import a_flow


def test_a_flow_of_the_tenant_exists_for_the_cycles() -> None:
    tenant_id, store = TenantId.new(), FlowStore()
    flow = a_flow(tenant_id)
    store.flows.extend((a_flow(tenant_id, name="beta"), flow))

    assert FlowDirectoryFromFlows(InMemoryFlowRepositoryAdapter(store, tenant_id)).exists(flow.id.value)


def test_a_flow_of_another_tenant_or_never_created_does_not_exist() -> None:
    tenant_id, store = TenantId.new(), FlowStore()
    foreign = a_flow(TenantId.new())
    store.flows.append(foreign)
    directory = FlowDirectoryFromFlows(InMemoryFlowRepositoryAdapter(store, tenant_id))

    assert not directory.exists(foreign.id.value)
    assert not directory.exists(uuid4())
