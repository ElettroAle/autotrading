"""A failed cycle told by the name of its flow (R1.8.2)."""

from uuid import UUID, uuid4

import pytest

from autotrading.application.flows.errors import FlowNotFoundError
from autotrading.application.flows.notify_cycle_failure import NotifyCycleFailureUseCase
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.support.flows import a_flow

TENANT = TenantId.new()


class ToldFailures:
    def __init__(self) -> None:
        self.told: list[tuple[UUID, str, str]] = []

    def execute(self, flow_id: UUID, flow_name: str, reason: str) -> None:
        self.told.append((flow_id, flow_name, reason))


def test_the_failure_is_told_with_the_flow_by_its_id_and_name_and_the_reason() -> None:
    store, notices = FlowStore(), ToldFailures()
    flow = a_flow(TENANT, name="alfa")
    store.flows.append(flow)

    NotifyCycleFailureUseCase(InMemoryFlowRepositoryAdapter(store, TENANT), notices).execute(flow.id.value, "timeout")

    assert notices.told == [(flow.id.value, "alfa", "timeout")]


def test_a_flow_of_another_tenant_is_not_found_and_nothing_is_told() -> None:
    store, notices = FlowStore(), ToldFailures()
    theirs = a_flow(TenantId.new())
    store.flows.append(theirs)

    with pytest.raises(FlowNotFoundError):
        NotifyCycleFailureUseCase(InMemoryFlowRepositoryAdapter(store, TENANT), notices).execute(
            theirs.id.value, "timeout"
        )

    assert notices.told == []
    assert uuid4() != theirs.id.value
