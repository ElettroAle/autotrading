"""The flows the worker planned, found by the threads of their cycles (ADR 0042)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from autotrading.adapters.outbound.threads.planned_flows import ThreadsPlannedFlowsAdapter
from autotrading.application.flows.errors import FlowOfCycleNotFoundError
from autotrading.application.flows.ports import ScheduledFlow, TenantScheduledFlow
from autotrading.domain.flows.cycle_schedule import CycleSchedule
from autotrading.domain.tenancy.tenant_id import TenantId

ANCHOR = datetime(2026, 11, 13, 9, 0, tzinfo=UTC)


def planned(tenant_id: TenantId, anchor: datetime = ANCHOR) -> TenantScheduledFlow:
    return TenantScheduledFlow(tenant_id, ScheduledFlow(uuid4(), CycleSchedule(anchor, timedelta(minutes=15))))


def test_a_planned_flow_is_found_with_its_tenant_and_anchor() -> None:
    directory, entry = ThreadsPlannedFlowsAdapter(), planned(TenantId.new())

    directory.remember([entry])

    assert directory.tenant_of(entry.flow.flow_id) == entry.tenant_id
    assert directory.anchor_of(entry.flow.flow_id) == ANCHOR


def test_a_flow_planned_once_stays_known_when_it_is_no_longer_planned() -> None:
    directory, first, second = ThreadsPlannedFlowsAdapter(), planned(TenantId.new()), planned(TenantId.new())
    directory.remember([first])

    directory.remember([second])

    assert directory.tenant_of(first.flow.flow_id) == first.tenant_id
    assert directory.tenants() == {first.tenant_id, second.tenant_id}


def test_a_flow_never_planned_is_not_found() -> None:
    with pytest.raises(FlowOfCycleNotFoundError):
        ThreadsPlannedFlowsAdapter().tenant_of(uuid4())
