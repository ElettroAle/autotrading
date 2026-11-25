"""ADR memoria-del-flusso-con-motivo-lunghezza-e-scelta-delle-decisioni: the decisions of a flow read back from the
table of the decisions of its completed cycles, with their motive, the price of their execution, the PnL of the
positions they opened or closed and how and when those positions closed, under row level security."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import Engine

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.closed_position_repository import (
    SqlAlchemyClosedPositionRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.cycle_repository import SqlAlchemyCycleRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.order_repository import SqlAlchemyOrderRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.past_decisions import SqlAlchemyPastDecisionsAdapter
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_memory import EVERY_DECISION, OPENINGS_AND_CLOSINGS
from autotrading.domain.flows.memory_entry import PastDecision
from autotrading.domain.flows.recorded_decision import DecisionAction, RecordedDecision
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.flow_link import FlowLink
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.order import Order, OrderOrigin, OrderRequest, OrderSource
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_flow
from tests.support.orders import EXECUTION

pytestmark = pytest.mark.integration

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)
OPENED_AT, CLOSED_AT, HELD_AT = NOW - timedelta(hours=3), NOW - timedelta(hours=2), NOW - timedelta(hours=1)
WINDOW = TimeWindow(NOW - timedelta(days=30), NOW)


def new_flow(database: Engine, tenant_id: TenantId | None = None) -> tuple[TenantId, Flow]:
    if tenant_id is None:
        tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
        SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
        tenant_id = tenant.id
    account = an_account(tenant_id, f"conto-{uuid4()}", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant_id).add(account)
    flow = a_flow(tenant_id, name=f"alfa-{uuid4()}", account_id=account.id.value)
    SqlAlchemyFlowRepositoryAdapter(database, tenant_id).add(flow)
    return tenant_id, flow


def decided(database: Engine, flow: Flow, planned_at: datetime, *decisions: RecordedDecision) -> None:
    cycle = CycleRecord(flow.id.value, planned_at, CycleOutcome.COMPLETED, decisions=decisions)
    SqlAlchemyCycleRepositoryAdapter(database, flow.tenant_id).record(cycle)


def executed(flow: Flow, planned_at: datetime, price: str, *, reduce_only: bool = False) -> Order:
    market_order = replace(
        MarketOrder.opening("BTC", Direction.LONG, Decimal("0.0002"), Slippage.default()), reduce_only=reduce_only
    )
    source = OrderSource(OrderOrigin.FLOW, flow=FlowLink(flow.id.value, planned_at, "BTC"))
    request = OrderRequest(flow.assigned_account_id, source, 2, market_order)
    return Order.executed(request, replace(EXECUTION, average_price=Decimal(price), executed_at=planned_at))


def closed(flow: Flow, realized_pnl: Decimal) -> ClosedPosition:
    return ClosedPosition(
        tenant_id=flow.tenant_id,
        flow_id=flow.id,
        asset="BTC",
        side=TradeSide.LONG,
        leverage=2,
        margin=Decimal(50),
        opening=PositionEnd(Decimal(100000), OPENED_AT, OPENED_AT),
        closing=PositionEnd(Decimal(102000), CLOSED_AT, CLOSED_AT),
        fees=Decimal("0.08"),
        reason=CloseReason.STOP_LOSS,
        realized_pnl=realized_pnl,
    )


def test_the_decisions_read_back_with_price_and_pnl_of_the_positions_newest_first(database: Engine) -> None:
    tenant_id, flow = new_flow(database)
    opening = RecordedDecision(
        "BTC", DecisionAction.OPEN, TradeSide.LONG, 80, "il mercato sale", motive="rottura", invalidation="sotto 99000"
    )
    closing = RecordedDecision("BTC", DecisionAction.CLOSE, None, 70, "obiettivo")
    holding = RecordedDecision("BTC", DecisionAction.OPEN, TradeSide.LONG, 75, "di nuovo")
    decided(database, flow, OPENED_AT, opening)
    decided(database, flow, CLOSED_AT, closing)
    decided(database, flow, HELD_AT, holding, RecordedDecision("ETH", DecisionAction.HOLD, None, 50, "laterale"))
    orders = SqlAlchemyOrderRepositoryAdapter(database, tenant_id)
    orders.add(executed(flow, OPENED_AT, "100000"))
    orders.add(executed(flow, CLOSED_AT, "102000", reduce_only=True))
    orders.add(executed(flow, HELD_AT, "101000"))
    SqlAlchemyClosedPositionRepositoryAdapter(database, tenant_id).add(closed(flow, Decimal(40)))

    past = SqlAlchemyPastDecisionsAdapter(database, tenant_id).past_decisions(
        flow.id.value, WINDOW, OPENINGS_AND_CLOSINGS
    )

    assert past == [
        PastDecision(HELD_AT, holding, Decimal(101000), None, position_open=True, opened_at=HELD_AT),
        PastDecision(CLOSED_AT, closing, Decimal(102000), Decimal(40)),
        PastDecision(
            OPENED_AT,
            opening,
            Decimal(100000),
            Decimal(40),
            closed_by=CloseReason.STOP_LOSS,
            opened_at=OPENED_AT,
            closed_at=CLOSED_AT,
        ),
    ]


def test_only_the_decisions_of_the_flow_in_the_window_are_read(database: Engine) -> None:
    tenant_id, alfa = new_flow(database)
    _, beta = new_flow(database, tenant_id)
    update = RecordedDecision("BTC", DecisionAction.UPDATE, None, 60, "stop")
    decided(database, alfa, HELD_AT, update)
    decided(database, alfa, NOW - timedelta(days=40), update)
    decided(database, beta, HELD_AT, RecordedDecision("BTC", DecisionAction.CLOSE, None, 60, "di beta"))

    past = SqlAlchemyPastDecisionsAdapter(database, tenant_id).past_decisions(alfa.id.value, WINDOW, EVERY_DECISION)

    assert past == [PastDecision(HELD_AT, update, None, None)]


def test_only_the_decisions_with_the_actions_asked_are_read(database: Engine) -> None:
    tenant_id, flow = new_flow(database)
    closing = RecordedDecision("BTC", DecisionAction.CLOSE, None, 60, "obiettivo")
    decided(database, flow, OPENED_AT, closing)
    decided(database, flow, CLOSED_AT, RecordedDecision("BTC", DecisionAction.UPDATE, None, 60, "stop"))
    decided(database, flow, HELD_AT, RecordedDecision("BTC", DecisionAction.HOLD, None, 60, "attesa"))

    adapter = SqlAlchemyPastDecisionsAdapter(database, tenant_id)

    assert adapter.past_decisions(flow.id.value, WINDOW, OPENINGS_AND_CLOSINGS) == [
        PastDecision(OPENED_AT, closing, None, None)
    ]


def test_a_cycle_that_failed_after_deciding_gives_no_decision(database: Engine) -> None:
    tenant_id, flow = new_flow(database)
    failed = CycleRecord(
        flow.id.value,
        HELD_AT,
        CycleOutcome.FAILED,
        decisions=(RecordedDecision("BTC", DecisionAction.CLOSE, None, 60, "fallito"),),
    )
    SqlAlchemyCycleRepositoryAdapter(database, tenant_id).record(failed)

    assert (
        SqlAlchemyPastDecisionsAdapter(database, tenant_id).past_decisions(flow.id.value, WINDOW, EVERY_DECISION) == []
    )


def test_another_tenant_never_reads_the_decisions(database: Engine) -> None:
    _, flow = new_flow(database)
    decided(database, flow, HELD_AT, RecordedDecision("BTC", DecisionAction.CLOSE, None, 60, "obiettivo"))
    other, _ = new_flow(database)

    assert SqlAlchemyPastDecisionsAdapter(database, other).past_decisions(flow.id.value, WINDOW, EVERY_DECISION) == []
