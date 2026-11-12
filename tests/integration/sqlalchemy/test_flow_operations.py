from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_ledger import SqlAlchemyFlowLedgerAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_operations import SqlAlchemyFlowOperationsAdapter
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.application.flows.errors import FlowAccountNotFoundError
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.ledger import (
    AccountLedger,
    Execution,
    ExecutionKind,
    FundingEntry,
    FundingPayment,
    LedgerEntry,
)
from autotrading.domain.flows.operations import FUNDING, Operation, OperationSource, OperationsQuery
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account

pytestmark = pytest.mark.integration

NOON = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)


def new_account(database: Engine) -> tuple[TenantId, UUID]:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, f"conto-{uuid4()}", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    return tenant.id, account.id.value


def an_execution(fill_id: str, executed_at: datetime, *, size: Decimal = Decimal(1), asset: str = "BTC") -> Execution:
    return Execution(
        fill_id,
        f"o-{fill_id}",
        uuid4(),
        asset,
        size,
        Decimal("100.5"),
        Decimal("0.1"),
        Decimal(3),
        Decimal(0),
        False,
        executed_at,
    )


def of_flow(flow_id: FlowId | None, *executions: Execution, funding: tuple[FundingEntry, ...] = ()) -> AccountLedger:
    kind = ExecutionKind.UNATTRIBUTED if flow_id is None else ExecutionKind.FLOW_ORDER
    return AccountLedger(tuple(LedgerEntry(execution, flow_id, kind, True) for execution in executions), funding)


def test_the_operations_of_a_flow_are_its_executions_and_funding_newest_first(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    flow_id = FlowId.new()
    funding = (FundingEntry(FundingPayment("BTC", Decimal("-0.25"), NOON + timedelta(minutes=2)), flow_id),)
    recorded = of_flow(
        flow_id,
        an_execution("acquisto", NOON, size=Decimal(2)),
        an_execution("vendita", NOON + timedelta(minutes=1), size=Decimal("-0.5")),
        funding=funding,
    )
    SqlAlchemyFlowLedgerAdapter(database, tenant_id).record(account_id, recorded, NOON)

    page = SqlAlchemyFlowOperationsAdapter(database, tenant_id).of_flow(flow_id, OperationsQuery())

    rows = [(o.kind, o.occurred_at, o.size, o.price, o.fee, o.realized_pnl, o.funding) for o in page.operations]
    assert rows == [
        (FUNDING, NOON + timedelta(minutes=2), None, None, Decimal(0), Decimal(0), Decimal("-0.25")),
        (
            ExecutionKind.FLOW_ORDER.value,
            NOON + timedelta(minutes=1),
            Decimal("-0.5"),
            Decimal("100.5"),
            Decimal("0.1"),
            Decimal(3),
            Decimal(0),
        ),
        (ExecutionKind.FLOW_ORDER.value, NOON, Decimal(2), Decimal("100.5"), Decimal("0.1"), Decimal(3), Decimal(0)),
    ]
    assert page.next is None


def test_the_pages_of_a_flow_follow_one_another_without_gaps_or_repeats(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    flow_id = FlowId.new()
    executions = [an_execution(f"f-{minute}", NOON + timedelta(minutes=minute // 2)) for minute in range(7)]
    funding = (FundingEntry(FundingPayment("BTC", Decimal(1), NOON + timedelta(minutes=1)), flow_id),)
    SqlAlchemyFlowLedgerAdapter(database, tenant_id).record(
        account_id, of_flow(flow_id, *executions, funding=funding), NOON
    )
    operations = SqlAlchemyFlowOperationsAdapter(database, tenant_id)

    seen: list[Operation] = []
    query = OperationsQuery(limit=3)
    while True:
        page = operations.of_flow(flow_id, query)
        seen.extend(page.operations)
        if page.next is None:
            break
        query = OperationsQuery(after=page.next, limit=3)

    cursors = [operation.cursor for operation in seen]
    assert len(seen) == 8
    assert cursors == sorted(cursors, reverse=True)
    assert len(set(cursors)) == 8
    assert seen[3].cursor.source == OperationSource.FUNDING


def test_the_operations_of_a_flow_are_filtered_by_asset_and_by_period(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    flow_id = FlowId.new()
    recorded = of_flow(
        flow_id,
        an_execution("prima", NOON - timedelta(hours=1)),
        an_execution("dentro", NOON),
        an_execution("altro-asset", NOON, asset="ETH"),
        an_execution("alla-fine", NOON + timedelta(hours=1)),
    )
    SqlAlchemyFlowLedgerAdapter(database, tenant_id).record(account_id, recorded, NOON)
    query = OperationsQuery(asset="BTC", since=NOON, until=NOON + timedelta(hours=1))

    page = SqlAlchemyFlowOperationsAdapter(database, tenant_id).of_flow(flow_id, query)

    assert [(operation.asset, operation.occurred_at) for operation in page.operations] == [("BTC", NOON)]


def test_the_operations_of_an_account_are_only_those_of_no_flow(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    ledger = SqlAlchemyFlowLedgerAdapter(database, tenant_id)
    ledger.record(account_id, of_flow(FlowId.new(), an_execution("del-flusso", NOON)), NOON)
    outside = FundingEntry(FundingPayment("SOL", Decimal(2), NOON + timedelta(minutes=1)), None)
    ledger.record(account_id, of_flow(None, an_execution("fuori", NOON, asset="SOL"), funding=(outside,)), NOON)

    page = SqlAlchemyFlowOperationsAdapter(database, tenant_id).unattributed_of_account(account_id, OperationsQuery())

    assert [(operation.kind, operation.asset) for operation in page.operations] == [
        (FUNDING, "SOL"),
        (ExecutionKind.UNATTRIBUTED.value, "SOL"),
    ]


def test_another_tenant_sees_nothing_of_the_operations(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    flow_id = FlowId.new()
    ledger = SqlAlchemyFlowLedgerAdapter(database, tenant_id)
    ledger.record(account_id, of_flow(flow_id, an_execution("del-flusso", NOON)), NOON)
    ledger.record(account_id, of_flow(None, an_execution("fuori", NOON)), NOON)
    other_tenant, _ = new_account(database)
    theirs = SqlAlchemyFlowOperationsAdapter(database, other_tenant)

    assert theirs.of_flow(flow_id, OperationsQuery()).operations == ()
    with pytest.raises(FlowAccountNotFoundError):
        theirs.unattributed_of_account(account_id, OperationsQuery())
