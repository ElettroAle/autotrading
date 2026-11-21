from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.execution import Execution
from autotrading.domain.orders.flow_link import FlowLink
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.order import Order, OrderOrigin, OrderRequest, OrderSource
from autotrading.domain.orders.rejection import Rejection
from autotrading.domain.orders.slippage import Slippage

EXECUTED_AT = datetime(2026, 11, 10, 12, 0, 1, tzinfo=UTC)
CYCLE_PLANNED_AT = datetime(2026, 11, 12, 10, 15, tzinfo=UTC)
EXECUTION = Execution(Decimal("0.0002"), Decimal("100030.5"), Decimal("0.009003"), Decimal("-0.25"), EXECUTED_AT)


def a_request(account_id: UUID, source: OrderSource | None = None) -> OrderRequest:
    market_order = MarketOrder.opening("BTC", Direction.LONG, Decimal("0.0002"), Slippage.default())
    return OrderRequest(account_id, source or OrderSource(OrderOrigin.VERIFICATION), 2, market_order)


def an_executed_order(account_id: UUID) -> Order:
    return Order.executed(a_request(account_id, OrderSource(OrderOrigin.MANUAL, "oid-anna")), EXECUTION)


def a_rejected_order(account_id: UUID) -> Order:
    return Order.rejected(a_request(account_id), Rejection.of("Insufficient margin to place order. asset=0"))


def a_flow_order(account_id: UUID, flow_id: UUID | None = None) -> Order:
    link = FlowLink(uuid4() if flow_id is None else flow_id, CYCLE_PLANNED_AT, "BTC")
    return Order.executed(a_request(account_id, OrderSource(OrderOrigin.FLOW, flow=link)), EXECUTION)


def a_flow_closing_order(account_id: UUID, flow_id: UUID) -> Order:
    """The closing of a position of a flow at a command of its user (stop, cash-out, emergency): reduce only, for the
    flow it closes (ADR chiusure-dei-flussi-con-il-flusso-nell-ordine)."""
    closing = MarketOrder("BTC", Direction.LONG, Decimal("0.0002"), Slippage.default(), reduce_only=True)
    source = OrderSource(OrderOrigin.MANUAL, "oid-anna", closing_flow_id=flow_id)
    return Order.executed(OrderRequest(account_id, source, 2, closing), EXECUTION)
