from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from autotrading.application.orders.ports import (
    FlowClosingRecorderPort,
    OrderRejectedNoticePort,
    PositionOpenedNoticePort,
)
from autotrading.domain.orders.order import Order


@dataclass(frozen=True, slots=True)
class FollowFlowOrdersCommand:
    flow_id: UUID
    flow_name: str
    cycle: datetime
    orders: tuple[Order, ...]


@dataclass(frozen=True, slots=True)
class FlowOrderFollowers:
    """Who hears what an order of a cycle left behind: a refusal, an opening, a closing."""

    rejections: OrderRejectedNoticePort
    openings: PositionOpenedNoticePort
    closings: FlowClosingRecorderPort


class FollowFlowOrdersUseCase:
    """Tells what each order of a cycle of the flow left behind: a refusal, an opening or a closing (R1.7.2, R1.8.2).

    An order without an outcome tells nothing: the reconciliation finds what the exchange did with it (R1.6.2).
    """

    def __init__(self, followers: FlowOrderFollowers) -> None:
        self._followers = followers

    def execute(self, command: FollowFlowOrdersCommand) -> None:
        for order in command.orders:
            self._follow(command, order)

    def _follow(self, command: FollowFlowOrdersCommand, order: Order) -> None:
        if order.rejection is not None:
            self._followers.rejections.execute(command.flow_name, order.rejection.exchange_message)
            return
        execution = order.execution
        if execution is None:
            return
        market_order = order.request.market_order
        if market_order.reduce_only:
            self._followers.closings.execute(command.flow_id, command.cycle, market_order.coin, execution)
            return
        self._followers.openings.execute(
            command.flow_name, market_order.coin, market_order.direction.value, order.request.leverage, execution.value
        )
