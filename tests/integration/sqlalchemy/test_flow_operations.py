from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_ledger import SqlAlchemyFlowLedgerAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_operations import EXPORT_BATCH, SqlAlchemyFlowOperationsAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
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
from autotrading.domain.flows.operations import (
    FUNDING,
    AccountOperations,
    AccountScope,
    FlowOperations,
    Operation,
    OperationSource,
    OperationsQuery,
    OperationsTotals,
)
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_flow

pytestmark = pytest.mark.integration

NOON = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)
EVERYTHING = OperationsQuery()


def new_account(database: Engine) -> tuple[TenantId, UUID]:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, f"conto-{uuid4()}", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    return tenant.id, account.id.value


def new_flow(database: Engine, tenant_id: TenantId, account_id: UUID, name: str) -> FlowId:
    flow = a_flow(tenant_id, name=name, account_id=account_id)
    SqlAlchemyFlowRepositoryAdapter(database, tenant_id).add(flow)
    return flow.id


def an_execution(
    fill_id: str,
    executed_at: datetime,
    *,
    size: Decimal = Decimal(1),
    asset: str = "BTC",
    fee: Decimal = Decimal("0.1"),
    realized_pnl: Decimal = Decimal(3),
) -> Execution:
    return Execution(
        fill_id,
        f"o-{fill_id}",
        uuid4(),
        asset,
        size,
        Decimal("100.5"),
        fee,
        realized_pnl,
        Decimal(0),
        False,
        executed_at,
    )


def of_flow(flow_id: FlowId | None, *executions: Execution, funding: tuple[FundingEntry, ...] = ()) -> AccountLedger:
    kind = ExecutionKind.UNATTRIBUTED if flow_id is None else ExecutionKind.FLOW_ORDER
    return AccountLedger(tuple(LedgerEntry(execution, flow_id, kind, True) for execution in executions), funding)


def page_of_flow(adapter: SqlAlchemyFlowOperationsAdapter, flow_id: FlowId, query: OperationsQuery) -> list[Operation]:
    return list(adapter.report(FlowOperations(flow_id), query).page.operations)


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

    report = SqlAlchemyFlowOperationsAdapter(database, tenant_id).report(FlowOperations(flow_id), EVERYTHING)

    rows = [(o.kind, o.occurred_at, o.size, o.price, o.fee, o.realized_pnl, o.funding) for o in report.page.operations]
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
    assert report.page.next is None


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
        page = operations.report(FlowOperations(flow_id), query).page
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

    found = page_of_flow(SqlAlchemyFlowOperationsAdapter(database, tenant_id), flow_id, query)

    assert [(operation.asset, operation.occurred_at) for operation in found] == [("BTC", NOON)]


def test_the_totals_cover_every_row_of_the_filter_whatever_the_page(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    flow_id = FlowId.new()
    executions = [
        an_execution(f"f-{minute}", NOON + timedelta(minutes=minute), fee=Decimal("0.5"), realized_pnl=Decimal(2))
        for minute in range(5)
    ]
    outside_period = an_execution("prima", NOON - timedelta(hours=1), realized_pnl=Decimal(100))
    funding = (FundingEntry(FundingPayment("BTC", Decimal("-0.25"), NOON + timedelta(minutes=1)), flow_id),)
    recorded = of_flow(flow_id, outside_period, *executions, funding=funding)
    SqlAlchemyFlowLedgerAdapter(database, tenant_id).record(account_id, recorded, NOON)
    operations = SqlAlchemyFlowOperationsAdapter(database, tenant_id)
    first = operations.report(FlowOperations(flow_id), OperationsQuery(since=NOON, limit=2))

    second = operations.report(FlowOperations(flow_id), OperationsQuery(since=NOON, after=first.page.next, limit=2))

    expected = OperationsTotals(6, Decimal(10), Decimal("2.5"), Decimal("-0.25"))
    assert first.totals == second.totals == expected


def test_the_totals_of_nothing_are_zero(database: Engine) -> None:
    tenant_id, _ = new_account(database)

    report = SqlAlchemyFlowOperationsAdapter(database, tenant_id).report(FlowOperations(FlowId.new()), EVERYTHING)

    assert report.totals == OperationsTotals(0, Decimal(0), Decimal(0), Decimal(0))


def test_each_row_names_its_flow_or_none(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    alfa = new_flow(database, tenant_id, account_id, "alfa")
    beta = new_flow(database, tenant_id, account_id, "beta")
    ledger = SqlAlchemyFlowLedgerAdapter(database, tenant_id)
    ledger.record(account_id, of_flow(alfa, an_execution("alfa", NOON)), NOON)
    beta_funding = (FundingEntry(FundingPayment("ETH", Decimal(1), NOON + timedelta(minutes=1)), beta),)
    ledger.record(account_id, of_flow(beta, funding=beta_funding), NOON)
    ledger.record(account_id, of_flow(None, an_execution("fuori", NOON + timedelta(minutes=2), asset="SOL")), NOON)
    owner = AccountOperations(account_id, AccountScope.ALL)

    report = SqlAlchemyFlowOperationsAdapter(database, tenant_id).report(owner, EVERYTHING)

    assert [(operation.asset, operation.flow) for operation in report.page.operations] == [
        ("SOL", None),
        ("ETH", "beta"),
        ("BTC", "alfa"),
    ]
    assert report.totals.count == 3


def test_the_operations_of_an_account_of_no_flow_leave_out_those_of_the_flows(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    ledger = SqlAlchemyFlowLedgerAdapter(database, tenant_id)
    ledger.record(account_id, of_flow(FlowId.new(), an_execution("del-flusso", NOON)), NOON)
    outside = FundingEntry(FundingPayment("SOL", Decimal(2), NOON + timedelta(minutes=1)), None)
    ledger.record(account_id, of_flow(None, an_execution("fuori", NOON, asset="SOL"), funding=(outside,)), NOON)
    owner = AccountOperations(account_id, AccountScope.UNATTRIBUTED)

    report = SqlAlchemyFlowOperationsAdapter(database, tenant_id).report(owner, EVERYTHING)

    assert [(operation.kind, operation.asset) for operation in report.page.operations] == [
        (FUNDING, "SOL"),
        (ExecutionKind.UNATTRIBUTED.value, "SOL"),
    ]
    assert report.totals == OperationsTotals(2, Decimal(3), Decimal("0.1"), Decimal(2))


def test_the_export_reads_every_row_of_the_filter_oldest_first_beyond_one_batch(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    flow_id = new_flow(database, tenant_id, account_id, "alfa")
    count = EXPORT_BATCH + 7
    executions = [an_execution(f"f-{second}", NOON + timedelta(seconds=second)) for second in range(count)]
    funding = (FundingEntry(FundingPayment("BTC", Decimal(1), NOON), flow_id),)
    SqlAlchemyFlowLedgerAdapter(database, tenant_id).record(
        account_id, of_flow(flow_id, *executions, funding=funding), NOON
    )
    query = OperationsQuery(since=NOON, after=None)

    exported = list(SqlAlchemyFlowOperationsAdapter(database, tenant_id).export(FlowOperations(flow_id), query))

    cursors = [operation.cursor for operation in exported]
    assert len(exported) == count + 1
    assert cursors == sorted(cursors)
    assert (exported[1].kind, exported[1].flow) == (FUNDING, "alfa")


def test_the_export_ignores_the_page(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    flow_id = FlowId.new()
    executions = [an_execution(f"f-{minute}", NOON + timedelta(minutes=minute)) for minute in range(3)]
    SqlAlchemyFlowLedgerAdapter(database, tenant_id).record(account_id, of_flow(flow_id, *executions), NOON)
    operations = SqlAlchemyFlowOperationsAdapter(database, tenant_id)
    first = operations.report(FlowOperations(flow_id), OperationsQuery(limit=1)).page

    exported = list(operations.export(FlowOperations(flow_id), OperationsQuery(after=first.next, limit=1)))

    assert len(exported) == 3


def test_the_export_of_an_account_the_tenant_does_not_have_is_refused_before_any_row(database: Engine) -> None:
    tenant_id, _ = new_account(database)
    operations = SqlAlchemyFlowOperationsAdapter(database, tenant_id)

    with pytest.raises(FlowAccountNotFoundError):
        operations.export(AccountOperations(uuid4(), AccountScope.ALL), EVERYTHING)


def test_another_tenant_sees_nothing_of_the_operations(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    flow_id = new_flow(database, tenant_id, account_id, "alfa")
    ledger = SqlAlchemyFlowLedgerAdapter(database, tenant_id)
    ledger.record(account_id, of_flow(flow_id, an_execution("del-flusso", NOON)), NOON)
    ledger.record(account_id, of_flow(None, an_execution("fuori", NOON)), NOON)
    other_tenant, _ = new_account(database)
    theirs = SqlAlchemyFlowOperationsAdapter(database, other_tenant)

    report = theirs.report(FlowOperations(flow_id), EVERYTHING)
    assert (report.page.operations, report.totals.count) == ((), 0)
    assert list(theirs.export(FlowOperations(flow_id), EVERYTHING)) == []
    with pytest.raises(FlowAccountNotFoundError):
        theirs.report(AccountOperations(account_id, AccountScope.ALL), EVERYTHING)
