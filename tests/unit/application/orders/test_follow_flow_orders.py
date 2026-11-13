"""What an order of a flow leaves behind: a refusal or an opening told, a closing recorded (R1.7.2, R1.8.2)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from autotrading.application.orders.follow_flow_orders import (
    FlowOrderFollowers,
    FollowFlowOrdersCommand,
    FollowFlowOrdersUseCase,
)
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.execution import Execution
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.order import Order, OrderOrigin, OrderRequest, OrderSource
from autotrading.domain.orders.slippage import Slippage
from tests.support.orders import EXECUTION, a_rejected_order, a_request

ACCOUNT = uuid4()
FLOW = uuid4()
CYCLE = datetime(2026, 11, 13, 9, tzinfo=UTC)


class RecordedEvents:
    def __init__(self) -> None:
        self.events: list[tuple[object, ...]] = []


class Rejections:
    def __init__(self, recorded: RecordedEvents) -> None:
        self._recorded = recorded

    def execute(self, flow_name: str, message: str) -> None:
        self._recorded.events.append(("rifiutato", flow_name, message))


class Openings:
    def __init__(self, recorded: RecordedEvents) -> None:
        self._recorded = recorded

    def execute(self, flow_name: str, asset: str, direction: str, leverage: int, value: Decimal) -> None:
        self._recorded.events.append(("aperto", flow_name, asset, direction, leverage, value))


class Closings:
    def __init__(self, recorded: RecordedEvents) -> None:
        self._recorded = recorded

    def execute(self, flow_id: UUID, cycle: datetime, asset: str, fill: Execution) -> None:
        self._recorded.events.append(("chiuso", flow_id, cycle, asset, fill))


def follow(*orders: Order) -> list[tuple[object, ...]]:
    recorded = RecordedEvents()
    followers = FlowOrderFollowers(Rejections(recorded), Openings(recorded), Closings(recorded))
    FollowFlowOrdersUseCase(followers).execute(FollowFlowOrdersCommand(FLOW, "Trend BTC", CYCLE, orders))
    return recorded.events


def a_closing() -> Order:
    market_order = MarketOrder("ETH", Direction.LONG, Decimal("0.5"), Slippage.default(), reduce_only=True)
    return Order.executed(OrderRequest(ACCOUNT, OrderSource(OrderOrigin.FLOW), 3, market_order), EXECUTION)


def test_a_refused_order_is_told_with_the_message_of_the_exchange() -> None:
    assert follow(a_rejected_order(ACCOUNT)) == [
        ("rifiutato", "Trend BTC", "Insufficient margin to place order. asset=0")
    ]


def test_an_order_without_outcome_tells_nothing() -> None:
    assert follow(Order.unknown(a_request(ACCOUNT))) == []


def test_an_executed_opening_is_told_with_direction_leverage_and_the_value_it_put_on_the_market() -> None:
    opening = Order.executed(a_request(ACCOUNT), EXECUTION)

    assert follow(opening) == [("aperto", "Trend BTC", "BTC", "long", 2, EXECUTION.value)]


def test_an_executed_closing_is_recorded_for_the_flow_and_cycle_with_its_execution() -> None:
    assert follow(a_closing()) == [("chiuso", FLOW, CYCLE, "ETH", EXECUTION)]


def test_every_order_is_followed_in_the_order_sent() -> None:
    events = follow(a_closing(), a_rejected_order(ACCOUNT))

    assert [event[0] for event in events] == ["chiuso", "rifiutato"]
