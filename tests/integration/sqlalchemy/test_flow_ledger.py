from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_ledger import SqlAlchemyFlowLedgerAdapter
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.ledger import (
    AccountLedger,
    Execution,
    ExecutionKind,
    FlowTotals,
    FundingEntry,
    FundingPayment,
    LedgerEntry,
)
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account

pytestmark = pytest.mark.integration

READ_AT = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
EARLIER = READ_AT - timedelta(minutes=10)


def new_account(database: Engine) -> tuple[TenantId, UUID]:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, f"conto-{uuid4()}", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    return tenant.id, account.id.value


def an_execution(
    fill_id: str,
    *,
    size: Decimal = Decimal(1),
    realized_pnl: Decimal = Decimal(0),
    fee: Decimal = Decimal(0),
    executed_at: datetime = READ_AT,
    asset: str = "BTC",
) -> Execution:
    return Execution(
        fill_id, f"o-{fill_id}", uuid4(), asset, size, Decimal(100), fee, realized_pnl, Decimal(0), False, executed_at
    )


def of_flow(flow_id: FlowId | None, *executions: Execution, funding: tuple[FundingEntry, ...] = ()) -> AccountLedger:
    kind = ExecutionKind.UNATTRIBUTED if flow_id is None else ExecutionKind.FLOW_ORDER
    return AccountLedger(tuple(LedgerEntry(execution, flow_id, kind, True) for execution in executions), funding)


def test_the_executions_enter_the_ledger_and_the_totals_of_their_flow(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    flow_id, ledger = FlowId.new(), SqlAlchemyFlowLedgerAdapter(database, tenant_id)
    payment = FundingEntry(FundingPayment("BTC", Decimal("-0.5"), READ_AT), flow_id)
    recorded = of_flow(
        flow_id,
        an_execution("1", size=Decimal(2), realized_pnl=Decimal(5), fee=Decimal(1), executed_at=EARLIER),
        an_execution("2", size=Decimal("-0.5"), realized_pnl=Decimal(-2), fee=Decimal("0.5"), asset="ETH"),
        funding=(payment,),
    )

    added = ledger.record(account_id, recorded, READ_AT)

    assert added == recorded.entries
    assert ledger.totals_of([flow_id]) == {
        flow_id: FlowTotals(
            flow_id, Decimal(3), Decimal("1.5"), Decimal("-0.5"), {"BTC": Decimal(2), "ETH": Decimal("-0.5")}
        )
    }
    assert ledger.cursor(account_id) == READ_AT


def test_an_execution_recorded_twice_is_counted_once(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    flow_id, ledger = FlowId.new(), SqlAlchemyFlowLedgerAdapter(database, tenant_id)
    payment = FundingEntry(FundingPayment("BTC", Decimal(1), READ_AT), flow_id)
    recorded = of_flow(flow_id, an_execution("1", realized_pnl=Decimal(5)), funding=(payment,))
    ledger.record(account_id, recorded, READ_AT)

    again = ledger.record(account_id, recorded, READ_AT)

    assert again == ()
    totals = ledger.totals_of([flow_id])[flow_id]
    assert (totals.realized_pnl, totals.funding, totals.expected("BTC")) == (Decimal(5), Decimal(1), Decimal(1))


def test_the_totals_equal_the_sums_of_the_whole_ledger(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    flow_id, ledger = FlowId.new(), SqlAlchemyFlowLedgerAdapter(database, tenant_id)
    for index in range(5):
        payment = FundingEntry(FundingPayment("BTC", Decimal("0.1"), READ_AT + timedelta(hours=index)), flow_id)
        execution = an_execution(str(index), realized_pnl=Decimal(index), fee=Decimal("0.2"), size=Decimal(-1) ** index)
        ledger.record(account_id, of_flow(flow_id, execution, funding=(payment,)), READ_AT)

    assert ledger.recomputed_totals(flow_id) == ledger.totals_of([flow_id])[flow_id]


def test_a_flow_without_any_execution_has_no_totals(database: Engine) -> None:
    tenant_id, _ = new_account(database)

    assert SqlAlchemyFlowLedgerAdapter(database, tenant_id).totals_of([FlowId.new()]) == {}


def test_an_execution_of_no_flow_is_recorded_without_totals(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    ledger = SqlAlchemyFlowLedgerAdapter(database, tenant_id)

    added = ledger.record(account_id, of_flow(None, an_execution("1")), READ_AT)

    assert len(added) == 1
    assert ledger.recorded_since(account_id, EARLIER).executions == frozenset({("1", "o-1")})


def test_the_keys_recorded_since_a_moment_are_only_the_newer_ones(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    ledger = SqlAlchemyFlowLedgerAdapter(database, tenant_id)
    old = FundingEntry(FundingPayment("BTC", Decimal(1), EARLIER), None)
    new = FundingEntry(FundingPayment("BTC", Decimal(1), READ_AT), None)
    recorded = of_flow(None, an_execution("1", executed_at=EARLIER), an_execution("2"), funding=(old, new))
    ledger.record(account_id, recorded, READ_AT)

    keys = ledger.recorded_since(account_id, READ_AT)

    assert (keys.executions, keys.funding) == (frozenset({("2", "o-2")}), frozenset({("BTC", READ_AT)}))


def test_a_late_cycle_never_moves_the_cursor_back(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    ledger = SqlAlchemyFlowLedgerAdapter(database, tenant_id)
    ledger.record(account_id, of_flow(None, an_execution("2")), READ_AT)

    ledger.record(account_id, of_flow(None, an_execution("1", executed_at=EARLIER)), EARLIER)

    assert ledger.cursor(account_id) == READ_AT


def test_an_account_without_a_ledger_has_no_cursor(database: Engine) -> None:
    tenant_id, account_id = new_account(database)

    assert SqlAlchemyFlowLedgerAdapter(database, tenant_id).cursor(account_id) is None


def test_another_tenant_sees_nothing_of_the_ledger(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    bruno, _ = new_account(database)
    flow_id = FlowId.new()
    SqlAlchemyFlowLedgerAdapter(database, tenant_id).record(account_id, of_flow(flow_id, an_execution("1")), READ_AT)
    theirs = SqlAlchemyFlowLedgerAdapter(database, bruno)

    assert theirs.cursor(account_id) is None
    assert theirs.totals_of([flow_id]) == {}
    assert theirs.recorded_since(account_id, EARLIER).executions == frozenset()


def test_the_ledger_of_an_account_of_another_tenant_cannot_be_written(database: Engine) -> None:
    _, account_id = new_account(database)
    bruno, _ = new_account(database)

    with pytest.raises(IntegrityError, match="account_fills_account_of_tenant"):
        SqlAlchemyFlowLedgerAdapter(database, bruno).record(account_id, of_flow(None, an_execution("1")), READ_AT)


def test_the_history_cannot_be_changed_by_the_application(database: Engine) -> None:
    tenant_id, account_id = new_account(database)
    SqlAlchemyFlowLedgerAdapter(database, tenant_id).record(account_id, of_flow(None, an_execution("1")), READ_AT)

    statements = (
        "UPDATE account_fills SET fee = 0",
        "DELETE FROM account_fills",
        "UPDATE account_funding SET amount = 0",
        "DELETE FROM account_funding",
    )
    for statement in statements:
        with database.begin() as connection:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
            with pytest.raises(ProgrammingError, match="permission denied"):
                connection.execute(text(statement))
