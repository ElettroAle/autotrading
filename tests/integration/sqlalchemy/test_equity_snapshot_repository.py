from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.equity_snapshot_repository import (
    SqlAlchemyEquitySnapshotRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.equity_period import EquityWindow
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_flow

pytestmark = pytest.mark.integration

PLANNED = datetime(2026, 11, 12, 10, 15, tzinfo=UTC)
EVERY_CYCLE = EquityWindow(None, None)


def new_flow(database: Engine) -> tuple[TenantId, UUID]:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, f"conto-{uuid4()}", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    flow = a_flow(tenant.id, name=f"flusso-{uuid4()}", account_id=account.id.value)
    SqlAlchemyFlowRepositoryAdapter(database, tenant.id).add(flow)
    return tenant.id, flow.id.value


def snapshot(flow_id: UUID, planned_at: datetime, realized_pnl: str = "4") -> EquitySnapshot:
    return EquitySnapshot(
        flow_id, planned_at, Decimal(300), Decimal(realized_pnl), Decimal("3.5"), Decimal("1.25"), Decimal("-0.1")
    )


def test_the_equity_of_a_cycle_reads_back_with_every_part_and_no_rounding(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    equity = SqlAlchemyEquitySnapshotRepositoryAdapter(database, tenant_id)

    equity.record(snapshot(flow_id, PLANNED))

    assert equity.of_flow(flow_id, EVERY_CYCLE) == [snapshot(flow_id, PLANNED)]


def test_the_cycles_come_from_the_oldest_across_the_months(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    equity = SqlAlchemyEquitySnapshotRepositoryAdapter(database, tenant_id)
    # December 2030 is the last monthly partition, 2031 falls in the default one.
    instants = [datetime(2031, 2, 1, tzinfo=UTC), PLANNED, datetime(2030, 12, 31, 23, 45, tzinfo=UTC)]

    for instant in instants:
        equity.record(snapshot(flow_id, instant))

    assert [item.planned_at for item in equity.of_flow(flow_id, EVERY_CYCLE)] == sorted(instants)


def test_a_window_reads_from_its_start_included_to_its_end_excluded(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    equity = SqlAlchemyEquitySnapshotRepositoryAdapter(database, tenant_id)
    for days in range(4):
        equity.record(snapshot(flow_id, PLANNED + timedelta(days=days)))

    found = equity.of_flow(flow_id, EquityWindow(PLANNED + timedelta(days=1), PLANNED + timedelta(days=3)))

    assert [item.planned_at for item in found] == [PLANNED + timedelta(days=1), PLANNED + timedelta(days=2)]


def test_a_cycle_keeps_its_first_equity(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    equity = SqlAlchemyEquitySnapshotRepositoryAdapter(database, tenant_id)

    equity.record(snapshot(flow_id, PLANNED, realized_pnl="4"))
    equity.record(snapshot(flow_id, PLANNED, realized_pnl="9"))

    assert [item.realized_pnl for item in equity.of_flow(flow_id, EVERY_CYCLE)] == [Decimal(4)]


def test_the_equity_of_a_tenant_is_invisible_to_another_tenant(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    other_tenant, _ = new_flow(database)
    SqlAlchemyEquitySnapshotRepositoryAdapter(database, tenant_id).record(snapshot(flow_id, PLANNED))

    assert SqlAlchemyEquitySnapshotRepositoryAdapter(database, other_tenant).of_flow(flow_id, EVERY_CYCLE) == []


def test_a_query_without_any_filter_sees_only_the_rows_of_its_tenant(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    other_tenant, _ = new_flow(database)
    SqlAlchemyEquitySnapshotRepositoryAdapter(database, tenant_id).record(snapshot(flow_id, PLANNED))

    for tenant in (other_tenant, None):
        with database.begin() as connection:
            if tenant is not None:
                connection.execute(select(func.set_config("app.tenant_id", str(tenant.value), True)))
            assert connection.execute(text("SELECT count(*) FROM equity_snapshots")).scalar_one() == 0


def test_a_tenant_cannot_record_the_equity_of_the_flow_of_another_tenant(database: Engine) -> None:
    _, flow_id = new_flow(database)
    other_tenant, _ = new_flow(database)

    with pytest.raises(IntegrityError):
        SqlAlchemyEquitySnapshotRepositoryAdapter(database, other_tenant).record(snapshot(flow_id, PLANNED))


def test_a_recorded_equity_is_never_changed_nor_deleted_nor_read_from_a_partition(database: Engine) -> None:
    tenant_id, flow_id = new_flow(database)
    SqlAlchemyEquitySnapshotRepositoryAdapter(database, tenant_id).record(snapshot(flow_id, PLANNED))

    statements = (
        "UPDATE equity_snapshots SET equity = 0",
        "DELETE FROM equity_snapshots",
        "SELECT * FROM equity_snapshots_2026_11",
    )
    for statement in statements:
        with database.begin() as connection:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
            with pytest.raises(ProgrammingError, match="permission denied"):
                connection.execute(text(statement))
