"""ADR riparazione-delle-chiusure-attribuite-a-un-altro-flusso: the closing of a stopped flow, recorded without its flow
and whose executions the ledger gave to the flow that took its asset, goes back to the flow it closed with its
executions, and the totals of both flows are summed again; a manual command from the dashboard stays without a flow
and with the flow that holds the asset; a second run changes nothing (R1.6.3, Bug 684).
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, Executable, RowMapping, func, select

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.closed_position_repository import (
    SqlAlchemyClosedPositionRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.flow_ledger import SqlAlchemyFlowLedgerAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.order_repository import SqlAlchemyOrderRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tables import account_fills, orders
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.ledger import AccountLedger, Execution, ExecutionKind, FlowTotals, LedgerEntry
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.execution import Execution as OrderExecution
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.order import Order, OrderOrigin, OrderRequest, OrderSource
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_configuration, a_flow
from tests.support.orders import a_flow_order
from tests.support.postgres import database_migrated_to

pytestmark = pytest.mark.integration

BEFORE_THE_REPAIR = "0054"
OPENED_AT = datetime(2026, 11, 21, 13, 41, 18, 120000, tzinfo=UTC)
STOPPED_AT = datetime(2026, 11, 21, 13, 41, 53, 640000, tzinfo=UTC)
CLOSED_BY_HAND_AT = datetime(2026, 11, 21, 15, 2, 7, 310000, tzinfo=UTC)
SIZE = Decimal("0.00298")


@dataclass(frozen=True, slots=True)
class Account:
    """The account of the case of dev: the stopped flow, the flow that took its asset, and their orders."""

    tenant_id: TenantId
    account_id: UUID
    stopped: Flow
    receiving: Flow
    closing_id: UUID
    manual_id: UUID


def a_closing(account_id: UUID, asset: str, executed_at: datetime) -> Order:
    """A closing at a command of the user, recorded without a flow as the platform did before the repair."""
    market_order = MarketOrder(asset, Direction.LONG, SIZE, Slippage.default(), reduce_only=True)
    request = OrderRequest(account_id, OrderSource(OrderOrigin.MANUAL, "oid-anna"), 2, market_order)
    return Order.executed(request, OrderExecution(SIZE, Decimal(84000), Decimal("0.11"), Decimal("-1.2"), executed_at))


def an_execution(fill_id: str, order_id: UUID, asset: str, size: Decimal, executed_at: datetime) -> Execution:
    return Execution(
        fill_id=fill_id,
        exchange_order_id=f"o-{fill_id}",
        order_id=order_id,
        asset=asset,
        size=size,
        price=Decimal(84000),
        fee=Decimal("0.05"),
        realized_pnl=Decimal("-0.6") if size < 0 else Decimal(0),
        start_position=-size if size < 0 else Decimal(0),
        liquidation=False,
        executed_at=executed_at,
    )


def a_closed_position(flow: Flow, asset: str, closed_at: datetime, reason: CloseReason) -> ClosedPosition:
    return ClosedPosition(
        tenant_id=flow.tenant_id,
        flow_id=flow.id,
        asset=asset,
        side=TradeSide.LONG,
        leverage=2,
        margin=Decimal(125),
        opening=PositionEnd(Decimal(84100), OPENED_AT, OPENED_AT),
        closing=PositionEnd(Decimal(84000), closed_at),
        fees=Decimal("0.21"),
        reason=reason,
    )


def the_case_of_dev(database: Engine) -> Account:
    """Stop of the flow with BTC open, BTC passed to another flow, the closing read by that flow's cycle; then a manual
    closing from the dashboard of the ETH of the other flow."""
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, f"conto-{uuid4()}", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    account_id, flows = account.id.value, SqlAlchemyFlowRepositoryAdapter(database, tenant.id)
    stopped = a_flow(tenant.id, name="BTC #1", account_id=account_id)
    receiving = a_flow(
        tenant.id, name="ETH + SOL #1", account_id=account_id, configuration=a_configuration(assets=("ETH", "BTC"))
    )
    flows.add(stopped)
    flows.add(receiving)
    opening, closing = a_flow_order(account_id, stopped.id.value), a_closing(account_id, "BTC", STOPPED_AT)
    manual = a_closing(account_id, "ETH", CLOSED_BY_HAND_AT)
    recorded_orders = SqlAlchemyOrderRepositoryAdapter(database, tenant.id)
    for order in (opening, closing, manual):
        recorded_orders.add(order)
    closed_positions = SqlAlchemyClosedPositionRepositoryAdapter(database, tenant.id)
    closed_positions.add(a_closed_position(stopped, "BTC", STOPPED_AT, CloseReason.FLOW_STOP))
    closed_positions.add(a_closed_position(receiving, "ETH", CLOSED_BY_HAND_AT, CloseReason.MANUAL))
    half = SIZE / 2
    executions = (
        (an_execution("1", opening.id.value, "BTC", SIZE, OPENED_AT), stopped),
        # The cycle of the flow that took BTC read the closing first, and gave it to that flow.
        (an_execution("2", closing.id.value, "BTC", -half, STOPPED_AT), receiving),
        (an_execution("3", closing.id.value, "BTC", -half, STOPPED_AT), receiving),
        (an_execution("4", uuid4(), "ETH", SIZE, OPENED_AT), receiving),
        (an_execution("5", manual.id.value, "ETH", -SIZE, CLOSED_BY_HAND_AT), receiving),
    )
    entries = tuple(
        LedgerEntry(execution, owner.id, ExecutionKind.FLOW_ORDER, platform_order=True)
        for execution, owner in executions
    )
    ledger = SqlAlchemyFlowLedgerAdapter(database, tenant.id)
    ledger.record(account_id, AccountLedger(entries, ()), CLOSED_BY_HAND_AT + timedelta(minutes=1))
    return Account(tenant.id, account_id, stopped, receiving, closing.id.value, manual.id.value)


def rows(database: Engine, tenant_id: TenantId, statement: Executable) -> list[RowMapping]:
    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
        return list(connection.execute(statement).mappings())


def flow_of_order(database: Engine, case: Account, order_id: UUID) -> UUID | None:
    (row,) = rows(database, case.tenant_id, select(orders.c.flow_id).where(orders.c.id == order_id))
    flow_id: UUID | None = row["flow_id"]
    return flow_id


def flows_of_executions(database: Engine, case: Account, order_id: UUID) -> list[tuple[UUID | None, str]]:
    statement = (
        select(account_fills.c.flow_id, account_fills.c.kind)
        .where(account_fills.c.order_id == order_id)
        .order_by(account_fills.c.fill_id)
    )
    return [(row["flow_id"], row["kind"]) for row in rows(database, case.tenant_id, statement)]


def totals(database: Engine, case: Account, flow: Flow) -> FlowTotals:
    return SqlAlchemyFlowLedgerAdapter(database, case.tenant_id).totals_of((flow.id,))[flow.id]


def summed_again(database: Engine, case: Account, flow: Flow) -> bool:
    """Whether the totals of the flow are those its ledger sums to; a position of zero is no position."""
    kept = totals(database, case, flow)
    summed = SqlAlchemyFlowLedgerAdapter(database, case.tenant_id).recomputed_totals(FlowId(flow.id.value))
    return (kept.realized_pnl, kept.fees, kept.funding, _held(kept)) == (
        summed.realized_pnl,
        summed.fees,
        summed.funding,
        _held(summed),
    )


def _held(flow_totals: FlowTotals) -> dict[str, Decimal]:
    return {asset: size for asset, size in flow_totals.positions.items() if size != 0}


def assert_repaired(database: Engine, case: Account) -> None:
    stopped, receiving = case.stopped, case.receiving
    assert flow_of_order(database, case, case.closing_id) == stopped.id.value
    assert flows_of_executions(database, case, case.closing_id) == [
        (stopped.id.value, ExecutionKind.FLOW_ORDER.value),
        (stopped.id.value, ExecutionKind.FLOW_ORDER.value),
    ]
    assert totals(database, case, stopped).expected("BTC") == 0
    assert totals(database, case, receiving).expected("BTC") == 0
    assert summed_again(database, case, stopped)
    assert summed_again(database, case, receiving)


def test_the_closing_of_a_stopped_flow_goes_back_to_it_with_its_executions(tmp_path: Path) -> None:
    with database_migrated_to(tmp_path, BEFORE_THE_REPAIR) as (database, migrate_the_rest):
        case = the_case_of_dev(database)
        assert totals(database, case, case.receiving).expected("BTC") == -SIZE

        migrate_the_rest()

        assert_repaired(database, case)
        assert totals(database, case, case.stopped).realized_pnl == Decimal("-1.2")
        assert totals(database, case, case.receiving).realized_pnl == Decimal("-0.6")


def test_a_manual_closing_from_the_dashboard_stays_with_the_flow_holding_the_asset(tmp_path: Path) -> None:
    with database_migrated_to(tmp_path, BEFORE_THE_REPAIR) as (database, migrate_the_rest):
        case = the_case_of_dev(database)

        migrate_the_rest()

        assert flow_of_order(database, case, case.manual_id) is None
        assert flows_of_executions(database, case, case.manual_id) == [
            (case.receiving.id.value, ExecutionKind.FLOW_ORDER.value)
        ]
        assert totals(database, case, case.receiving).expected("ETH") == 0


def test_a_second_run_of_the_repair_changes_nothing(tmp_path: Path) -> None:
    with database_migrated_to(tmp_path, BEFORE_THE_REPAIR) as (database, migrate_the_rest):
        case = the_case_of_dev(database)

        migrate_the_rest(again_from=BEFORE_THE_REPAIR)

        assert_repaired(database, case)
        assert totals(database, case, case.stopped).realized_pnl == Decimal("-1.2")
