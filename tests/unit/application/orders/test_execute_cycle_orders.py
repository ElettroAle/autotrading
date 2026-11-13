"""The orders a cycle of a flow got through the risk check: sent, recorded, and then followed (R1.5.5, R1.7.2)."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from autotrading.application.orders.execute_cycle_orders import ExecuteCycleOrdersUseCase
from autotrading.application.orders.execute_flow_orders import ExecuteFlowOrdersUseCase
from autotrading.application.orders.follow_flow_orders import FlowOrderFollowers, FollowFlowOrdersUseCase
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.slippage import Slippage
from tests.fakes.order_exchange import FakeOrderExchangeAdapter
from tests.fakes.order_repository import InMemoryOrderRepositoryAdapter
from tests.fakes.trading_access import FakeTradingAccessAdapter
from tests.support.trading import HYPERLIQUID, new_access

FLOW_ID = uuid4()
PLANNED_AT = datetime(2026, 11, 12, 10, 15, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class Opening:
    asset: str
    side: str
    value: Decimal
    leverage: int

    def order_with[T](self, opening: Callable[[str, str, Decimal, int], T], closing: Callable[[str], T]) -> T:  # noqa: ARG002
        return opening(self.asset, self.side, self.value, self.leverage)


@dataclass(frozen=True, slots=True)
class Closing:
    asset: str

    def order_with[T](self, opening: Callable[[str, str, Decimal, int], T], closing: Callable[[str], T]) -> T:  # noqa: ARG002
        return closing(self.asset)


@dataclass(frozen=True, slots=True)
class CycleOrders:
    account_id: UUID
    flow_id: UUID
    flow_name: str
    planned_at: datetime
    orders: tuple[Opening | Closing, ...]


class Told:
    """Every follower of the orders at once: what the orders of the cycle left behind, in order."""

    def __init__(self) -> None:
        self.events: list[tuple[object, ...]] = []

    def execute(self, *event: object) -> None:
        self.events.append(event)

    def follow(self) -> FollowFlowOrdersUseCase:
        return FollowFlowOrdersUseCase(FlowOrderFollowers(self, self, self))


def test_the_orders_are_sent_closings_first_and_followed_with_the_name_of_the_flow() -> None:
    accesses, exchange, orders, told = (
        FakeTradingAccessAdapter(),
        FakeOrderExchangeAdapter(),
        InMemoryOrderRepositoryAdapter(),
        Told(),
    )
    account_id = uuid4()
    accesses.accesses[account_id] = new_access()
    exchange.hold(accesses.accesses[account_id], HeldPosition("ETH", Direction.LONG, Decimal("0.5"), 4))
    execute = ExecuteFlowOrdersUseCase(accesses.use_case, {HYPERLIQUID: exchange}, orders, Slippage.default())
    request = CycleOrders(
        account_id, FLOW_ID, "Trend BTC", PLANNED_AT, (Opening("BTC", "short", Decimal(200), 3), Closing("ETH"))
    )

    sent = ExecuteCycleOrdersUseCase(execute, told.follow()).execute(request)

    assert [order.request.market_order.coin for order in sent] == ["ETH", "BTC"]
    assert sent[1].request.market_order.direction is Direction.SHORT
    assert orders.orders == list(sent)
    closed, opened = told.events
    assert closed[:4] == (FLOW_ID, PLANNED_AT, "ETH", sent[0].execution)
    assert opened[:4] == ("Trend BTC", "BTC", "short", 3)


def test_a_cycle_without_orders_sends_and_follows_nothing() -> None:
    accesses, orders, told = FakeTradingAccessAdapter(), InMemoryOrderRepositoryAdapter(), Told()
    execute = ExecuteFlowOrdersUseCase(accesses.use_case, {}, orders, Slippage.default())

    sent = ExecuteCycleOrdersUseCase(execute, told.follow()).execute(CycleOrders(uuid4(), FLOW_ID, "x", PLANNED_AT, ()))

    assert sent == ()
    assert told.events == []
