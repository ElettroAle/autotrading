"""ADR stato-del-flusso-in-ogni-notifica: the state of a flow for its notifications, read on PostgreSQL under row level
security.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.equity_snapshot_repository import (
    SqlAlchemyEquitySnapshotRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.flow_ledger import SqlAlchemyFlowLedgerAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_status import SqlAlchemyFlowStatusAdapter
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.capital_change import CapitalChange, CapitalChangeReason
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.ledger import AccountLedger, Execution, ExecutionKind, LedgerEntry
from autotrading.domain.notifications.flow_status import FlowStatusFigures, NotifiedFlowStatus, RecordedEquity
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_configuration, a_flow

pytestmark = pytest.mark.integration

FIRST_CYCLE = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)
LAST_CYCLE = FIRST_CYCLE + timedelta(minutes=15)
CAPITAL = Decimal(300)


def new_account(database: Engine) -> tuple[TenantId, UUID]:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, f"conto-{uuid4()}", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    return tenant.id, account.id.value


def new_flow(database: Engine, name: str = "alfa", status: FlowStatus = FlowStatus.ACTIVE) -> tuple[TenantId, Flow]:
    tenant_id, account_id = new_account(database)
    flow = a_flow(
        tenant_id,
        name=name,
        status=status,
        account_id=account_id,
        configuration=a_configuration(allocated_capital=CAPITAL),
    )
    SqlAlchemyFlowRepositoryAdapter(database, tenant_id).add(flow)
    return tenant_id, flow


def record_equity(database: Engine, tenant_id: TenantId, flow: Flow, planned_at: datetime, pnl: str) -> None:
    snapshot = EquitySnapshot(
        flow.id.value, planned_at, CAPITAL, Decimal(pnl), Decimal(0), Decimal(0), Decimal(0), cashed_profit=Decimal(0)
    )
    SqlAlchemyEquitySnapshotRepositoryAdapter(database, tenant_id).record(snapshot)


def hold(database: Engine, tenant_id: TenantId, flow: Flow, *assets: str) -> None:
    entries = tuple(LedgerEntry(an_opening(asset), flow.id, ExecutionKind.FLOW_ORDER, True) for asset in assets)
    ledger = SqlAlchemyFlowLedgerAdapter(database, tenant_id)
    ledger.record(flow.assigned_account_id, AccountLedger(entries, ()), FIRST_CYCLE)


def an_opening(asset: str) -> Execution:
    zero = Decimal(0)
    return Execution(
        f"f-{asset}", f"o-{asset}", uuid4(), asset, Decimal(1), Decimal(100), zero, zero, zero, False, FIRST_CYCLE
    )


def test_the_state_is_the_one_of_the_last_cycle_recorded_with_the_positions_the_ledger_expects(
    database: Engine,
) -> None:
    tenant_id, flow = new_flow(database)
    record_equity(database, tenant_id, flow, FIRST_CYCLE, "5")
    record_equity(database, tenant_id, flow, LAST_CYCLE, "12.40")
    hold(database, tenant_id, flow, "BTC", "ETH")

    figures = SqlAlchemyFlowStatusAdapter(database, tenant_id, "USDC").status_of(flow.name.value)

    assert figures == FlowStatusFigures(
        NotifiedFlowStatus.ACTIVE, 2, "USDC", RecordedEquity(Decimal("312.40"), CAPITAL, Decimal(0))
    )


def test_the_profits_cashed_out_up_to_the_last_cycle_count_in_the_state(database: Engine) -> None:
    tenant_id, flow = new_flow(database)
    record_equity(database, tenant_id, flow, LAST_CYCLE, "30")
    cash_out = CapitalChange(
        flow.id,
        FIRST_CYCLE,
        CAPITAL,
        CAPITAL,
        UserId("oid-anna"),
        CapitalChangeReason.CASH_OUT,
        Decimal(18),
        value_before=CAPITAL + Decimal(18),
        cashed_profit=Decimal(18),
    )
    SqlAlchemyFlowRepositoryAdapter(database, tenant_id).add_capital_change(flow, cash_out)

    figures = SqlAlchemyFlowStatusAdapter(database, tenant_id, "USDC").status_of(flow.name.value)

    assert figures is not None
    assert figures.recorded == RecordedEquity(Decimal(330), CAPITAL, Decimal(18))


def test_a_flow_that_never_ran_a_cycle_has_no_recorded_equity(database: Engine) -> None:
    tenant_id, flow = new_flow(database, status=FlowStatus.STOPPED)

    figures = SqlAlchemyFlowStatusAdapter(database, tenant_id, "USDC").status_of(flow.name.value)

    assert figures == FlowStatusFigures(NotifiedFlowStatus.STOPPED, 0, "USDC", None)


def test_an_archived_flow_has_no_state_to_tell(database: Engine) -> None:
    tenant_id, flow = new_flow(database, status=FlowStatus.ARCHIVED)

    assert SqlAlchemyFlowStatusAdapter(database, tenant_id, "USDC").status_of(flow.name.value) is None


def test_another_tenant_never_reads_the_state_of_the_flow(database: Engine) -> None:
    tenant_id, flow = new_flow(database)
    record_equity(database, tenant_id, flow, LAST_CYCLE, "12.40")
    other_tenant, _ = new_account(database)

    assert SqlAlchemyFlowStatusAdapter(database, other_tenant, "USDC").status_of(flow.name.value) is None
