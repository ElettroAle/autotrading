from uuid import uuid4

import pytest

from autotrading.application.flows.errors import FlowAccountNotFoundError
from autotrading.application.flows.list_emergency_flows import ListEmergencyFlowsUseCase
from autotrading.application.flows.preview_emergency_closing import (
    PreviewEmergencyClosingCommand,
    PreviewEmergencyClosingUseCase,
)
from autotrading.domain.flows.emergency_closing import EmergencyClosingPreview, EmergencyScope
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.fakes.account_thresholds import FakeAccountThresholdsAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.support.activity import a_position, an_activity
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId.new()
ACCOUNT, OTHER_ACCOUNT = uuid4(), uuid4()


@pytest.fixture
def store() -> FlowStore:
    store = FlowStore()
    for name, asset, account_id in (
        ("alfa", "BTC", ACCOUNT),
        ("beta", "ETH", ACCOUNT),
        ("gamma", "SOL", OTHER_ACCOUNT),
    ):
        configuration = a_configuration(assets=(asset,))
        store.flows.append(
            a_flow(TENANT, name=name, status=FlowStatus.ACTIVE, account_id=account_id, configuration=configuration)
        )
    return store


@pytest.fixture
def activity() -> FakeAccountActivityAdapter:
    activity = FakeAccountActivityAdapter()
    activity.activities[ACCOUNT] = an_activity(positions=(a_position("BTC"), a_position("ETH"), a_position("DOGE")))
    activity.activities[OTHER_ACCOUNT] = an_activity(positions=(a_position("SOL"),))
    return activity


def preview_of(store: FlowStore, activity: FakeAccountActivityAdapter) -> PreviewEmergencyClosingUseCase:
    accounts = FakeAccountThresholdsAdapter({ACCOUNT: "test-1", OTHER_ACCOUNT: "test-2"})
    flows = ListEmergencyFlowsUseCase(InMemoryFlowRepositoryAdapter(store, TENANT), accounts)
    return PreviewEmergencyClosingUseCase(flows, activity)


def test_counts_the_flows_of_an_account_and_the_positions_they_hold(
    store: FlowStore, activity: FakeAccountActivityAdapter
) -> None:
    preview = preview_of(store, activity).execute(PreviewEmergencyClosingCommand(EmergencyScope(account_id=ACCOUNT)))

    assert preview == EmergencyClosingPreview(flows=2, positions=2)
    assert activity.read == [ACCOUNT]


def test_reads_each_account_once_for_every_flow(store: FlowStore, activity: FakeAccountActivityAdapter) -> None:
    preview = preview_of(store, activity).execute(PreviewEmergencyClosingCommand(EmergencyScope()))

    assert preview == EmergencyClosingPreview(flows=3, positions=3)
    assert sorted(activity.read) == sorted([ACCOUNT, OTHER_ACCOUNT])


def test_closes_nothing_to_preview(store: FlowStore, activity: FakeAccountActivityAdapter) -> None:
    preview_of(store, activity).execute(PreviewEmergencyClosingCommand(EmergencyScope()))

    assert all(flow.status is FlowStatus.ACTIVE for flow in store.flows)


def test_refuses_an_account_the_tenant_lacks(store: FlowStore, activity: FakeAccountActivityAdapter) -> None:
    with pytest.raises(FlowAccountNotFoundError):
        preview_of(store, activity).execute(PreviewEmergencyClosingCommand(EmergencyScope(account_id=uuid4())))
