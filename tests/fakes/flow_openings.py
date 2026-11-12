"""Fake of the openings of the flows, read from the orders the platform recorded, as the real adapter does."""

from autotrading.domain.flows.closed_position import PositionEnd
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.stop_outcome import PositionOpening
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.orders.order import OrderStatus
from tests.fakes.order_repository import InMemoryOrderRepositoryAdapter

EXECUTED = (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED)


class InMemoryFlowOpeningsAdapter:
    def __init__(self, orders: InMemoryOrderRepositoryAdapter) -> None:
        self._orders = orders

    def last_opening(self, flow_id: FlowId, asset: str) -> PositionOpening | None:
        openings = [
            order
            for order in self._orders.orders
            if order.request.source.flow is not None
            and order.request.source.flow.flow_id == flow_id.value
            and order.request.market_order.coin == asset
            and not order.request.market_order.reduce_only
            and order.status in EXECUTED
            and order.execution is not None
        ]
        if not openings:
            return None
        order = openings[-1]
        execution, link = order.execution, order.request.source.flow
        assert execution is not None
        assert link is not None
        margin = execution.filled_size * execution.average_price / order.request.leverage
        end = PositionEnd(execution.average_price, execution.executed_at, link.cycle_planned_at)
        side = TradeSide(order.request.market_order.direction.value)
        return PositionOpening(side, order.request.leverage, margin, end, execution.fee)
