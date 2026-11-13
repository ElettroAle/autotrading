from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.orders.errors import OrderExchangeUnavailableError, UnsupportedOrderExchangeError
from autotrading.application.orders.execute_flow_orders import ExecuteFlowOrdersCommand, ExecuteFlowOrdersUseCase
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.errors import LeverageAboveMaximumError
from autotrading.domain.orders.flow_link import FlowLink
from autotrading.domain.orders.flow_order import FlowClosing, FlowOpening, FlowOrder
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.order import OrderOrigin, OrderSource, OrderStatus
from autotrading.domain.orders.slippage import Slippage
from tests.fakes.order_exchange import FakeOrderExchangeAdapter
from tests.fakes.order_repository import InMemoryOrderRepositoryAdapter
from tests.fakes.trading_access import FakeTradingAccessAdapter
from tests.support.trading import HYPERLIQUID, new_access

SLIPPAGE = Slippage.percent(Decimal(2))
FLOW_ID = UUID("7d0c6a52-4b0e-4f7e-9c55-2f1d0b8e6a11")
PLANNED_AT = datetime(2026, 11, 12, 10, 15, tzinfo=UTC)
BTC = FlowOpening("BTC", Direction.SHORT, Decimal(200), 3)


@pytest.fixture
def exchange() -> FakeOrderExchangeAdapter:
    return FakeOrderExchangeAdapter()


@pytest.fixture
def orders() -> InMemoryOrderRepositoryAdapter:
    return InMemoryOrderRepositoryAdapter()


@pytest.fixture
def accesses() -> FakeTradingAccessAdapter:
    return FakeTradingAccessAdapter()


@pytest.fixture
def account_id(accesses: FakeTradingAccessAdapter) -> UUID:
    account_id = uuid4()
    accesses.accesses[account_id] = new_access()
    return account_id


@pytest.fixture
def use_case(
    accesses: FakeTradingAccessAdapter, exchange: FakeOrderExchangeAdapter, orders: InMemoryOrderRepositoryAdapter
) -> ExecuteFlowOrdersUseCase:
    return ExecuteFlowOrdersUseCase(accesses.use_case, {HYPERLIQUID: exchange}, orders, SLIPPAGE)


def command(account_id: UUID, *orders: FlowOrder) -> ExecuteFlowOrdersCommand:
    return ExecuteFlowOrdersCommand(account_id, FLOW_ID, PLANNED_AT, orders)


def hold_eth(exchange: FakeOrderExchangeAdapter, accesses: FakeTradingAccessAdapter, account_id: UUID) -> None:
    exchange.hold(accesses.accesses[account_id], HeldPosition("ETH", Direction.LONG, Decimal("0.5"), 4))


def test_an_opening_is_sized_at_the_market_with_its_leverage_and_slippage(
    use_case: ExecuteFlowOrdersUseCase,
    exchange: FakeOrderExchangeAdapter,
    accesses: FakeTradingAccessAdapter,
    account_id: UUID,
) -> None:
    (order,) = use_case.execute(command(account_id, BTC))

    (sent,) = exchange.sent
    assert (sent.coin, sent.direction, sent.size, sent.slippage, sent.reduce_only) == (
        "BTC",
        Direction.SHORT,
        Decimal("0.00200"),
        SLIPPAGE,
        False,
    )
    assert exchange.leverages[accesses.accesses[account_id].account_address, "BTC"] == 3
    assert (order.request.leverage, order.request.account_id, order.status) == (3, account_id, OrderStatus.FILLED)


def test_each_order_is_linked_to_the_flow_the_cycle_and_the_decision_on_its_asset(
    use_case: ExecuteFlowOrdersUseCase,
    exchange: FakeOrderExchangeAdapter,
    accesses: FakeTradingAccessAdapter,
    account_id: UUID,
) -> None:
    hold_eth(exchange, accesses, account_id)

    closing, opening = use_case.execute(command(account_id, BTC, FlowClosing("ETH")))

    assert closing.request.source == OrderSource(OrderOrigin.FLOW, flow=FlowLink(FLOW_ID, PLANNED_AT, "ETH"))
    assert opening.request.source == OrderSource(OrderOrigin.FLOW, flow=FlowLink(FLOW_ID, PLANNED_AT, "BTC"))


def test_a_closing_closes_the_whole_position_with_its_leverage(
    use_case: ExecuteFlowOrdersUseCase,
    exchange: FakeOrderExchangeAdapter,
    accesses: FakeTradingAccessAdapter,
    account_id: UUID,
) -> None:
    hold_eth(exchange, accesses, account_id)

    (order,) = use_case.execute(command(account_id, FlowClosing("ETH")))

    (sent,) = exchange.sent
    assert (sent.coin, sent.direction, sent.size, sent.reduce_only) == ("ETH", Direction.LONG, Decimal("0.5"), True)
    assert (order.request.leverage, order.status) == (4, OrderStatus.FILLED)


def test_every_order_is_recorded_with_the_real_outcome_in_the_sending_order(
    use_case: ExecuteFlowOrdersUseCase,
    exchange: FakeOrderExchangeAdapter,
    accesses: FakeTradingAccessAdapter,
    orders: InMemoryOrderRepositoryAdapter,
    account_id: UUID,
) -> None:
    hold_eth(exchange, accesses, account_id)
    exchange.fill_at = (Decimal(100050), Decimal("0.04"))

    executed = use_case.execute(command(account_id, BTC, FlowClosing("ETH")))

    assert orders.orders == list(executed)
    assert [order.request.market_order.coin for order in orders.orders] == ["ETH", "BTC"]
    assert [(order.execution.average_price, order.execution.fee) for order in executed if order.execution] == [
        (Decimal(100050), Decimal("0.04")),
        (Decimal(100050), Decimal("0.04")),
    ]


def test_a_refused_order_is_recorded_and_the_next_ones_are_sent(
    use_case: ExecuteFlowOrdersUseCase,
    exchange: FakeOrderExchangeAdapter,
    accesses: FakeTradingAccessAdapter,
    account_id: UUID,
) -> None:
    hold_eth(exchange, accesses, account_id)
    exchange.closing_rejection = "Order rejected"

    closing, opening = use_case.execute(command(account_id, FlowClosing("ETH"), BTC))

    assert closing.status is OrderStatus.REJECTED
    assert closing.rejection is not None
    assert closing.rejection.exchange_message == "Order rejected"
    assert opening.status is OrderStatus.FILLED


def test_a_refused_leverage_is_a_refused_order_and_the_next_ones_go_on(
    use_case: ExecuteFlowOrdersUseCase,
    exchange: FakeOrderExchangeAdapter,
    orders: InMemoryOrderRepositoryAdapter,
    account_id: UUID,
) -> None:
    exchange.leverage_rejection = "Invalid leverage value"
    eth = FlowOpening("ETH", Direction.LONG, Decimal(100), 2)

    refused, other = use_case.execute(command(account_id, BTC, eth))

    assert refused.status is OrderStatus.REJECTED
    assert refused.rejection is not None
    assert refused.rejection.exchange_message == "Invalid leverage value"
    assert refused.request.market_order.size == Decimal("0.00200")
    assert other.request.market_order.coin == "ETH"
    assert exchange.sent == []
    assert orders.orders == [refused, other]


def test_a_closing_without_a_position_on_the_exchange_sends_nothing(
    use_case: ExecuteFlowOrdersUseCase,
    exchange: FakeOrderExchangeAdapter,
    orders: InMemoryOrderRepositoryAdapter,
    account_id: UUID,
) -> None:
    executed = use_case.execute(command(account_id, FlowClosing("ETH"), BTC))

    assert [order.request.market_order.coin for order in executed] == ["BTC"]
    assert [order.coin for order in exchange.sent] == ["BTC"]
    assert len(orders.orders) == 1


def test_an_unreachable_exchange_stops_the_orders_and_keeps_the_ones_already_sent(
    use_case: ExecuteFlowOrdersUseCase,
    exchange: FakeOrderExchangeAdapter,
    accesses: FakeTradingAccessAdapter,
    orders: InMemoryOrderRepositoryAdapter,
    account_id: UUID,
) -> None:
    hold_eth(exchange, accesses, account_id)
    exchange.unreachable_after_orders = 1

    with pytest.raises(OrderExchangeUnavailableError):
        use_case.execute(command(account_id, FlowClosing("ETH"), BTC))

    assert [order.request.market_order.coin for order in orders.orders] == ["ETH"]


def test_an_exchange_the_platform_does_not_support_sends_nothing(
    exchange: FakeOrderExchangeAdapter,
    orders: InMemoryOrderRepositoryAdapter,
    accesses: FakeTradingAccessAdapter,
) -> None:
    account_id = uuid4()
    accesses.accesses[account_id] = new_access("Binance")
    use_case = ExecuteFlowOrdersUseCase(accesses.use_case, {HYPERLIQUID: exchange}, orders, SLIPPAGE)

    with pytest.raises(UnsupportedOrderExchangeError):
        use_case.execute(command(account_id, BTC))

    assert (exchange.sent, orders.orders) == ([], [])


def test_a_cycle_without_orders_never_opens_the_access_to_the_account(use_case: ExecuteFlowOrdersUseCase) -> None:
    # An account that cannot be opened would raise: without orders nothing asks for it.
    assert use_case.execute(command(uuid4())) == ()


def test_a_leverage_beyond_the_maximum_of_the_asset_sends_nothing(
    use_case: ExecuteFlowOrdersUseCase,
    exchange: FakeOrderExchangeAdapter,
    orders: InMemoryOrderRepositoryAdapter,
    account_id: UUID,
) -> None:
    with pytest.raises(LeverageAboveMaximumError):
        use_case.execute(command(account_id, FlowOpening("BTC", Direction.LONG, Decimal(100), 41)))

    assert (exchange.sent, exchange.leverages, orders.orders) == ([], {}, [])
