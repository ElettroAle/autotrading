from uuid import uuid4

import pytest

from autotrading.application.flows.errors import FlowAccountNotFoundError, FlowNotFoundError
from autotrading.application.flows.list_emergency_flows import ListEmergencyFlowsCommand, ListEmergencyFlowsUseCase
from autotrading.domain.flows.emergency_closing import EmergencyScope
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_thresholds import FakeAccountThresholdsAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.support.flows import a_flow

TENANT = TenantId.new()
ACCOUNT = uuid4()
EMPTY_ACCOUNT = uuid4()


def listing() -> tuple[ListEmergencyFlowsUseCase, FlowStore]:
    store = FlowStore()
    accounts = FakeAccountThresholdsAdapter({ACCOUNT: "test-1", EMPTY_ACCOUNT: "test-2"})
    return ListEmergencyFlowsUseCase(InMemoryFlowRepositoryAdapter(store, TENANT), accounts), store


def test_lists_the_active_and_paused_flows_of_the_scope() -> None:
    use_case, store = listing()
    alfa = a_flow(TENANT, name="alfa", status=FlowStatus.ACTIVE, account_id=ACCOUNT)
    beta = a_flow(TENANT, name="beta", status=FlowStatus.STOPPED, account_id=ACCOUNT)
    store.flows += [alfa, beta]

    assert use_case.execute(ListEmergencyFlowsCommand(EmergencyScope(account_id=ACCOUNT))) == (alfa,)


def test_an_account_without_flows_has_none_to_list() -> None:
    use_case, _ = listing()

    assert use_case.execute(ListEmergencyFlowsCommand(EmergencyScope(account_id=EMPTY_ACCOUNT))) == ()


def test_refuses_an_account_the_tenant_lacks() -> None:
    use_case, _ = listing()

    with pytest.raises(FlowAccountNotFoundError):
        use_case.execute(ListEmergencyFlowsCommand(EmergencyScope(account_id=uuid4())))


def test_refuses_a_flow_the_tenant_lacks() -> None:
    use_case, store = listing()
    store.flows.append(a_flow(TenantId.new(), status=FlowStatus.ACTIVE, account_id=ACCOUNT))

    with pytest.raises(FlowNotFoundError):
        use_case.execute(ListEmergencyFlowsCommand(EmergencyScope(flow_id=store.flows[0].id)))

    with pytest.raises(FlowNotFoundError):
        use_case.execute(ListEmergencyFlowsCommand(EmergencyScope(flow_id=FlowId.new())))


def test_lists_every_flow_of_the_tenant_without_a_scope() -> None:
    use_case, store = listing()
    alfa = a_flow(TENANT, name="alfa", status=FlowStatus.ACTIVE, account_id=ACCOUNT)
    gamma = a_flow(TENANT, name="gamma", status=FlowStatus.PAUSED, account_id=EMPTY_ACCOUNT)
    store.flows += [alfa, gamma, a_flow(TenantId.new(), status=FlowStatus.ACTIVE)]

    assert use_case.execute(ListEmergencyFlowsCommand(EmergencyScope())) == (alfa, gamma)
