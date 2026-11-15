import pytest

from autotrading.application.flows.read_flow_activity import ReadFlowActivityUseCase
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.support.flows import a_flow


@pytest.mark.parametrize(
    ("status", "runs"),
    [
        (FlowStatus.ACTIVE, True),
        (FlowStatus.PAUSED, False),
        (FlowStatus.STOPPED, False),
        (FlowStatus.ARCHIVED, False),
        (FlowStatus.DRAFT, False),
    ],
)
def test_only_an_active_flow_runs_its_cycle(status: FlowStatus, runs: bool) -> None:
    tenant_id = TenantId.new()
    repository = InMemoryFlowRepositoryAdapter(FlowStore(), tenant_id)
    flow = a_flow(tenant_id, status=status)
    repository.add(flow)

    assert ReadFlowActivityUseCase(repository).execute(flow.id.value) is runs
