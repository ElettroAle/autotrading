from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import Engine

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_openings import SqlAlchemyFlowOpeningsAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.order_repository import SqlAlchemyOrderRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.closed_position import PositionEnd
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.stop_outcome import PositionOpening
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.flow_link import FlowLink
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.order import Order, OrderOrigin, OrderRequest, OrderSource
from autotrading.domain.orders.rejection import Rejection
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_flow
from tests.support.orders import CYCLE_PLANNED_AT, EXECUTED_AT, EXECUTION

pytestmark = pytest.mark.integration


def new_flow(database: Engine) -> tuple[TenantId, Flow]:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    account = an_account(tenant.id, f"conto-{uuid4()}", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
    flow = a_flow(tenant.id, name=f"alfa-{uuid4()}", account_id=account.id.value)
    SqlAlchemyFlowRepositoryAdapter(database, tenant.id).add(flow)
    return tenant.id, flow


def a_request(flow: Flow, coin: str = "BTC", *, reduce_only: bool = False) -> OrderRequest:
    # The closing of a long position sells its size reduce-only: it is never an opening.
    opening = MarketOrder.opening(coin, Direction.LONG, Decimal("0.0002"), Slippage.default())
    market_order = replace(opening, reduce_only=reduce_only)
    link = FlowLink(flow.id.value, CYCLE_PLANNED_AT, coin)
    return OrderRequest(flow.assigned_account_id, OrderSource(OrderOrigin.FLOW, flow=link), 2, market_order)


def executed(request: OrderRequest, *, later_by: timedelta = timedelta(0), price: str = "100030.5") -> Order:
    return Order.executed(request, replace(EXECUTION, average_price=Decimal(price), executed_at=EXECUTED_AT + later_by))


def record(database: Engine, tenant_id: TenantId, *orders: Order) -> None:
    repository = SqlAlchemyOrderRepositoryAdapter(database, tenant_id)
    for order in orders:
        repository.add(order)


def test_the_opening_of_a_flow_is_its_executed_order_with_margin_at_price_over_leverage(database: Engine) -> None:
    tenant_id, flow = new_flow(database)
    record(database, tenant_id, executed(a_request(flow)))

    opening = SqlAlchemyFlowOpeningsAdapter(database, tenant_id).last_opening(flow.id, "BTC")

    assert opening == PositionOpening(
        TradeSide.LONG,
        2,
        Decimal("0.0002") * Decimal("100030.5") / 2,
        PositionEnd(Decimal("100030.5"), EXECUTED_AT, CYCLE_PLANNED_AT),
        Decimal("0.009003"),
    )


def test_the_last_executed_opening_on_the_asset_is_the_one_still_open(database: Engine) -> None:
    tenant_id, flow = new_flow(database)
    record(
        database,
        tenant_id,
        executed(a_request(flow), later_by=timedelta(hours=2), price="101000"),
        executed(a_request(flow), price="99000"),
        executed(a_request(flow, reduce_only=True), later_by=timedelta(hours=3), price="102000"),
        executed(a_request(flow, "ETH"), later_by=timedelta(hours=4), price="4000"),
        Order.rejected(a_request(flow), Rejection.of("Insufficient margin to place order. asset=0")),
    )

    opening = SqlAlchemyFlowOpeningsAdapter(database, tenant_id).last_opening(flow.id, "BTC")

    assert opening is not None
    assert (opening.end.price, opening.end.at) == (Decimal(101000), EXECUTED_AT + timedelta(hours=2))


def test_a_flow_without_executed_openings_on_the_asset_has_none(database: Engine) -> None:
    tenant_id, flow = new_flow(database)
    record(database, tenant_id, executed(a_request(flow, "ETH")))

    assert SqlAlchemyFlowOpeningsAdapter(database, tenant_id).last_opening(flow.id, "BTC") is None


def test_the_openings_of_another_tenant_are_never_read(database: Engine) -> None:
    tenant_id, flow = new_flow(database)
    other_tenant, _ = new_flow(database)
    record(database, tenant_id, executed(a_request(flow)))

    assert SqlAlchemyFlowOpeningsAdapter(database, other_tenant).last_opening(flow.id, "BTC") is None
