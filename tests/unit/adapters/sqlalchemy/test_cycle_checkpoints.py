from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import create_engine

from autotrading.adapters.outbound.sqlalchemy.cycle_checkpoints import SqlAlchemyCycleCheckpointsAdapter
from autotrading.domain.tenancy.tenant_id import TenantId

TENANT = TenantId(UUID("00000000-0000-0000-0000-00000000000a"))
FLOW = UUID("00000000-0000-0000-0000-0000000000f1")


def test_the_thread_of_a_cycle_starts_with_its_tenant_then_names_flow_and_planned_instant() -> None:
    checkpoints = SqlAlchemyCycleCheckpointsAdapter(create_engine("postgresql+psycopg://app@db/autotrading"), TENANT)

    thread = checkpoints.thread(FLOW, datetime(2026, 11, 13, 10, 0, tzinfo=UTC))

    assert thread == f"{TENANT.value}/{FLOW}/2026-11-13T10:00:00+00:00"
