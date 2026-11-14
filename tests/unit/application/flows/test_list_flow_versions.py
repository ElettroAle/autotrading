from datetime import UTC, datetime, timedelta

import pytest

from autotrading.application.flows.errors import FlowNotFoundError
from autotrading.application.flows.list_flow_versions import ListFlowVersionsCommand, ListFlowVersionsUseCase
from autotrading.application.flows.ports import FlowVersion
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.support.flows import a_configuration, a_flow

CREATED_AT = datetime(2026, 11, 14, 9, 30, tzinfo=UTC)


def test_the_versions_are_listed_newest_first_with_when_each_was_created() -> None:
    store = FlowStore()
    tenant_id = TenantId.new()
    repository = InMemoryFlowRepositoryAdapter(store, tenant_id)
    flow = a_flow(tenant_id)
    store.now = CREATED_AT
    repository.add(flow)
    for days, asset in ((1, "ETH"), (2, "SOL")):
        store.now = CREATED_AT + timedelta(days=days)
        repository.add_version(repository.get(flow.id).reconfigured(a_configuration(assets=(asset,))))

    versions = ListFlowVersionsUseCase(repository).execute(ListFlowVersionsCommand(flow.id))

    assert versions == (
        FlowVersion(3, CREATED_AT + timedelta(days=2)),
        FlowVersion(2, CREATED_AT + timedelta(days=1)),
        FlowVersion(1, CREATED_AT),
    )


def test_the_versions_of_a_flow_of_another_tenant_are_not_found() -> None:
    store = FlowStore()
    anna = TenantId.new()
    flow = a_flow(anna)
    InMemoryFlowRepositoryAdapter(store, anna).add(flow)
    bruno_flows = InMemoryFlowRepositoryAdapter(store, TenantId.new())

    for flow_id in (flow.id, FlowId.new()):
        with pytest.raises(FlowNotFoundError):
            ListFlowVersionsUseCase(bruno_flows).execute(ListFlowVersionsCommand(flow_id))
