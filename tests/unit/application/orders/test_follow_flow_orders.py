"""What an order of a flow leaves behind once sent: a refusal, an opening or a closing told to the flow (R1.8.2)."""

from decimal import Decimal
from uuid import uuid4

from autotrading.application.orders.follow_flow_orders import FollowFlowOrdersCommand, FollowFlowOrdersUseCase
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.execution import Execution
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.order import Order, OrderOrigin, OrderRequest, OrderSource
from autotrading.domain.orders.slippage import Slippage
from tests.support.orders import EXECUTION, a_rejected_order, a_request

ACCOUNT = uuid4()


class RecordedEvents:
    def __init__(self) -> None:
        self.events: list[tuple[object, ...]] = []

    def rejected(self, message: str) -> None:
        self.events.append(("rifiutato", message))

    def opened(self, coin: str, direction: str, leverage: int, value: Decimal) -> None:
        self.events.append(("aperto", coin, direction, leverage, value))

    def closed(self, coin: str, execution: Execution) -> None:
        self.events.append(("chiuso", coin, execution))


def follow(*orders: Order) -> list[tuple[object, ...]]:
    events = RecordedEvents()
    FollowFlowOrdersUseCase(events).execute(FollowFlowOrdersCommand(orders))
    return events.events


def a_closing() -> Order:
    market_order = MarketOrder("ETH", Direction.LONG, Decimal("0.5"), Slippage.default(), reduce_only=True)
    return Order.executed(OrderRequest(ACCOUNT, OrderSource(OrderOrigin.FLOW), 3, market_order), EXECUTION)


def test_a_refused_order_is_told_with_the_message_of_the_exchange() -> None:
    assert follow(a_rejected_order(ACCOUNT)) == [("rifiutato", "Insufficient margin to place order. asset=0")]


def test_an_order_without_outcome_tells_nothing() -> None:
    assert follow(Order.unknown(a_request(ACCOUNT))) == []


def test_an_executed_opening_is_told_with_direction_leverage_and_the_value_it_put_on_the_market() -> None:
    opening = Order.executed(a_request(ACCOUNT), EXECUTION)

    assert follow(opening) == [("aperto", "BTC", "long", 2, EXECUTION.value)]


def test_an_executed_closing_is_told_with_its_execution() -> None:
    assert follow(a_closing()) == [("chiuso", "ETH", EXECUTION)]


def test_every_order_is_followed_in_the_order_sent() -> None:
    events = follow(a_closing(), a_rejected_order(ACCOUNT))

    assert [event[0] for event in events] == ["chiuso", "rifiutato"]
