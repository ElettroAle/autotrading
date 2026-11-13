from decimal import Decimal

from autotrading.application.orders.execute_flow_orders import ExecuteFlowOrdersCommand, ExecuteFlowOrdersUseCase
from autotrading.application.orders.follow_flow_orders import FollowFlowOrdersCommand, FollowFlowOrdersUseCase
from autotrading.application.orders.ports import CycleOrdersPort
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.flow_order import FlowClosing, FlowOpening, FlowOrder
from autotrading.domain.orders.order import Order


class ExecuteCycleOrdersUseCase:
    """The approved orders of a cycle: sent on the account of the flow, then followed by what they left behind
    (R1.5.5, R1.7.2, R1.8.2).
    """

    def __init__(self, execute: ExecuteFlowOrdersUseCase, follow: FollowFlowOrdersUseCase) -> None:
        self._execute = execute
        self._follow = follow

    def execute(self, cycle: CycleOrdersPort) -> tuple[Order, ...]:
        orders = tuple(order.order_with(_opening, FlowClosing) for order in cycle.orders)
        sent = self._execute.execute(
            ExecuteFlowOrdersCommand(cycle.account_id, cycle.flow_id, cycle.planned_at, orders)
        )
        self._follow.execute(FollowFlowOrdersCommand(cycle.flow_id, cycle.flow_name, cycle.planned_at, sent))
        return sent


def _opening(asset: str, side: str, value: Decimal, leverage: int) -> FlowOrder:
    return FlowOpening(asset, Direction(side), value, leverage)
