from dataclasses import dataclass

from autotrading.application.orders.ports import FlowOrderEventsPort
from autotrading.domain.orders.order import Order


@dataclass(frozen=True, slots=True)
class FollowFlowOrdersCommand:
    orders: tuple[Order, ...]


class FollowFlowOrdersUseCase:
    """Tells the flow what each order of its cycle left behind: a refusal, an opening or a closing (R1.8.2).

    An order without an outcome tells nothing: the reconciliation finds what the exchange did with it (R1.6.2).
    """

    def __init__(self, events: FlowOrderEventsPort) -> None:
        self._events = events

    def execute(self, command: FollowFlowOrdersCommand) -> None:
        for order in command.orders:
            self._follow(order)

    def _follow(self, order: Order) -> None:
        if order.rejection is not None:
            self._events.rejected(order.rejection.exchange_message)
            return
        if order.execution is None:
            return
        market_order = order.request.market_order
        if market_order.reduce_only:
            self._events.closed(market_order.coin, order.execution)
            return
        self._events.opened(
            market_order.coin, market_order.direction.value, order.request.leverage, order.execution.value
        )
