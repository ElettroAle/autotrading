from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.orders.close_exchange_position import (
    CloseExchangePositionCommand,
    CloseExchangePositionUseCase,
)
from autotrading.application.orders.errors import NoOpenPositionError, OrderAccountNotFoundError
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.order import OrderOrigin, OrderSource, OrderStatus
from autotrading.domain.orders.slippage import Slippage
from tests.fakes.order_exchange import FakeOrderExchangeAdapter
from tests.fakes.order_repository import InMemoryOrderRepositoryAdapter
from tests.fakes.trading_access import FakeTradingAccessAdapter
from tests.support.trading import HYPERLIQUID, new_access

MANUAL = OrderSource(OrderOrigin.MANUAL, "oid-anna")
SLIPPAGE = Slippage.percent(Decimal(3))
SHORT_ETH = HeldPosition("ETH", Direction.SHORT, Decimal("1.5"), 4)


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
def account_id(accesses: FakeTradingAccessAdapter, exchange: FakeOrderExchangeAdapter) -> UUID:
    account_id = uuid4()
    accesses.accesses[account_id] = new_access()
    exchange.hold(accesses.accesses[account_id], SHORT_ETH)
    return account_id


@pytest.fixture
def use_case(
    accesses: FakeTradingAccessAdapter, exchange: FakeOrderExchangeAdapter, orders: InMemoryOrderRepositoryAdapter
) -> CloseExchangePositionUseCase:
    return CloseExchangePositionUseCase(accesses, {HYPERLIQUID: exchange}, orders, SLIPPAGE)


def test_closes_the_whole_position_with_a_reduce_only_order(
    use_case: CloseExchangePositionUseCase, exchange: FakeOrderExchangeAdapter, account_id: UUID
) -> None:
    order = use_case.execute(CloseExchangePositionCommand(account_id, "ETH", MANUAL))

    (sent,) = exchange.sent
    assert (sent.coin, sent.direction, sent.size, sent.reduce_only, sent.slippage) == (
        "ETH",
        Direction.SHORT,
        Decimal("1.5"),
        True,
        SLIPPAGE,
    )
    assert sent.is_buy
    assert order.status is OrderStatus.FILLED
    assert exchange.positions == {}


def test_the_close_is_recorded_with_the_source_of_the_command_and_the_leverage(
    use_case: CloseExchangePositionUseCase, orders: InMemoryOrderRepositoryAdapter, account_id: UUID
) -> None:
    order = use_case.execute(CloseExchangePositionCommand(account_id, "ETH", MANUAL))

    assert orders.orders == [order]
    assert order.request.source == MANUAL
    assert order.request.leverage == 4


def test_without_a_position_on_the_asset_nothing_is_sent_or_recorded(
    use_case: CloseExchangePositionUseCase,
    exchange: FakeOrderExchangeAdapter,
    orders: InMemoryOrderRepositoryAdapter,
    account_id: UUID,
) -> None:
    with pytest.raises(NoOpenPositionError) as raised:
        use_case.execute(CloseExchangePositionCommand(account_id, "BTC", MANUAL))

    assert str(raised.value) == "nessuna posizione aperta su BTC"
    assert (exchange.sent, orders.orders) == ([], [])


def test_a_refused_close_is_recorded_as_an_outcome(
    use_case: CloseExchangePositionUseCase,
    exchange: FakeOrderExchangeAdapter,
    orders: InMemoryOrderRepositoryAdapter,
    account_id: UUID,
) -> None:
    exchange.rejection = "Order could not immediately match against any resting orders. asset=4"

    order = use_case.execute(CloseExchangePositionCommand(account_id, "ETH", MANUAL))

    assert order.status is OrderStatus.REJECTED
    assert orders.orders == [order]
    assert exchange.position(new_access(), "ETH") is None


def test_an_account_the_tenant_does_not_have_is_not_found(
    use_case: CloseExchangePositionUseCase, exchange: FakeOrderExchangeAdapter
) -> None:
    with pytest.raises(OrderAccountNotFoundError):
        use_case.execute(CloseExchangePositionCommand(uuid4(), "ETH", MANUAL))

    assert exchange.sent == []
