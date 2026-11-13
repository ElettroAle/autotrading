"""The tenants of the flows the worker planned (ADR 0042)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from autotrading.adapters.outbound.threads.planned_flows import ThreadsPlannedFlowsAdapter
from autotrading.application.flows.ports import ScheduledFlow, TenantScheduledFlow
from autotrading.domain.flows.cycle_schedule import CycleSchedule
from autotrading.domain.tenancy.tenant_id import TenantId

ANCHOR = datetime(2026, 11, 13, 9, 0, tzinfo=UTC)


def planned(tenant_id: TenantId) -> TenantScheduledFlow:
    return TenantScheduledFlow(tenant_id, ScheduledFlow(uuid4(), CycleSchedule(ANCHOR, timedelta(minutes=15))))


def test_a_planned_flow_makes_its_tenant_known() -> None:
    directory, entry = ThreadsPlannedFlowsAdapter(), planned(TenantId.new())

    directory.remember([entry])

    assert directory.tenants() == {entry.tenant_id}


def test_a_tenant_planned_once_stays_known_when_its_flows_are_no_longer_planned() -> None:
    directory, first, second = ThreadsPlannedFlowsAdapter(), planned(TenantId.new()), planned(TenantId.new())
    directory.remember([first])

    directory.remember([second])

    assert directory.tenants() == {first.tenant_id, second.tenant_id}
