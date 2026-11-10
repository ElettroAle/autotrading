from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.execution import Execution
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.order import Order, OrderOrigin, OrderRequest, OrderSource
from autotrading.domain.orders.rejection import Rejection
from autotrading.domain.orders.slippage import Slippage

EXECUTED_AT = datetime(2026, 11, 10, 12, 0, 1, tzinfo=UTC)
EXECUTION = Execution(Decimal("0.0002"), Decimal("100030.5"), Decimal("0.009003"), Decimal("-0.25"), EXECUTED_AT)


def a_request(account_id: UUID, source: OrderSource | None = None) -> OrderRequest:
    market_order = MarketOrder.opening("BTC", Direction.LONG, Decimal("0.0002"), Slippage.default())
    return OrderRequest(account_id, source or OrderSource(OrderOrigin.VERIFICATION), 2, market_order)


def an_executed_order(account_id: UUID) -> Order:
    return Order.executed(a_request(account_id, OrderSource(OrderOrigin.MANUAL, "oid-anna")), EXECUTION)


def a_rejected_order(account_id: UUID) -> Order:
    return Order.rejected(a_request(account_id), Rejection.of("Insufficient margin to place order. asset=0"))
