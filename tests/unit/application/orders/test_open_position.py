from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.orders.errors import (
    OrderAccountNotFoundError,
    OrderExchangeUnavailableError,
    UnsupportedOrderExchangeError,
)
from autotrading.application.orders.open_position import OpenPositionCommand, OpenPositionUseCase
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.errors import LeverageAboveMaximumError, OrderSizeBelowStepError
from autotrading.domain.orders.order import OrderStatus
from autotrading.domain.orders.rejection import RejectionReason
from autotrading.domain.orders.slippage import Slippage
from tests.fakes.order_exchange import FakeOrderExchangeAdapter
from tests.fakes.order_repository import InMemoryOrderRepositoryAdapter
from tests.fakes.trading_access import FakeTradingAccessAdapter
from tests.support.trading import HYPERLIQUID, VERIFICATION, new_access

SLIPPAGE = Slippage.percent(Decimal(2))


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
) -> OpenPositionUseCase:
    return OpenPositionUseCase(accesses, {HYPERLIQUID: exchange}, orders, SLIPPAGE)


def opening(account_id: UUID, leverage: int = 3, value: str = "20") -> OpenPositionCommand:
    return OpenPositionCommand(account_id, "BTC", Direction.SHORT, leverage, Decimal(value), VERIFICATION)


def test_opens_with_the_leverage_the_size_and_the_slippage_asked(
    use_case: OpenPositionUseCase,
    exchange: FakeOrderExchangeAdapter,
    accesses: FakeTradingAccessAdapter,
    account_id: UUID,
) -> None:
    order = use_case.execute(opening(account_id))

    (sent,) = exchange.sent
    assert (sent.coin, sent.direction, sent.size, sent.slippage, sent.reduce_only) == (
        "BTC",
        Direction.SHORT,
        Decimal("0.0002"),
        SLIPPAGE,
        False,
    )
    assert exchange.leverages[accesses.access(account_id).account_address, "BTC"] == 3
    assert order.status is OrderStatus.FILLED


def test_the_order_is_recorded_with_its_request_and_outcome(
    use_case: OpenPositionUseCase, orders: InMemoryOrderRepositoryAdapter, account_id: UUID
) -> None:
    order = use_case.execute(opening(account_id))

    assert orders.orders == [order]
    assert (order.request.account_id, order.request.leverage, order.request.source) == (account_id, 3, VERIFICATION)


def test_a_leverage_beyond_the_maximum_sends_and_records_nothing(
    use_case: OpenPositionUseCase,
    exchange: FakeOrderExchangeAdapter,
    orders: InMemoryOrderRepositoryAdapter,
    account_id: UUID,
) -> None:
    with pytest.raises(LeverageAboveMaximumError):
        use_case.execute(opening(account_id, leverage=41))

    assert (exchange.sent, exchange.leverages, orders.orders) == ([], {}, [])


def test_a_value_below_one_step_sends_nothing(
    use_case: OpenPositionUseCase, exchange: FakeOrderExchangeAdapter, account_id: UUID
) -> None:
    with pytest.raises(OrderSizeBelowStepError):
        use_case.execute(opening(account_id, value="0.5"))

    assert exchange.sent == []


def test_a_refusal_is_an_outcome_recorded_once(
    use_case: OpenPositionUseCase,
    exchange: FakeOrderExchangeAdapter,
    orders: InMemoryOrderRepositoryAdapter,
    account_id: UUID,
) -> None:
    exchange.rejection = "Insufficient margin to place order. asset=0"

    order = use_case.execute(opening(account_id))

    assert order.status is OrderStatus.REJECTED
    assert order.rejection is not None
    assert order.rejection.reason is RejectionReason.INSUFFICIENT_MARGIN
    assert (len(exchange.sent), orders.orders) == (1, [order])


def test_an_order_without_answer_is_looked_up_and_its_execution_recorded(
    use_case: OpenPositionUseCase, exchange: FakeOrderExchangeAdapter, account_id: UUID
) -> None:
    exchange.silent = exchange.executes_when_silent = True

    order = use_case.execute(opening(account_id))

    assert exchange.lookups == [order.id]
    assert order.status is OrderStatus.FILLED
    assert order.execution == exchange.executions[order.id]


def test_an_order_without_answer_that_the_exchange_does_not_know_is_unknown(
    use_case: OpenPositionUseCase, exchange: FakeOrderExchangeAdapter, account_id: UUID
) -> None:
    exchange.silent = True

    order = use_case.execute(opening(account_id))

    assert exchange.lookups == [order.id]
    assert order.status is OrderStatus.UNKNOWN
    assert len(exchange.sent) == 1


def test_an_account_the_tenant_does_not_have_is_not_found(
    use_case: OpenPositionUseCase, exchange: FakeOrderExchangeAdapter
) -> None:
    with pytest.raises(OrderAccountNotFoundError):
        use_case.execute(opening(uuid4()))

    assert exchange.sent == []


def test_an_exchange_the_worker_does_not_support_is_refused(
    accesses: FakeTradingAccessAdapter, orders: InMemoryOrderRepositoryAdapter
) -> None:
    account_id = uuid4()
    accesses.accesses[account_id] = new_access("Binance")
    use_case = OpenPositionUseCase(accesses, {HYPERLIQUID: FakeOrderExchangeAdapter()}, orders, SLIPPAGE)

    with pytest.raises(UnsupportedOrderExchangeError) as raised:
        use_case.execute(opening(account_id))

    assert raised.value.supported == (HYPERLIQUID,)


def test_an_unreachable_exchange_records_nothing(
    use_case: OpenPositionUseCase,
    exchange: FakeOrderExchangeAdapter,
    orders: InMemoryOrderRepositoryAdapter,
    account_id: UUID,
) -> None:
    exchange.reachable = False

    with pytest.raises(OrderExchangeUnavailableError):
        use_case.execute(opening(account_id))

    assert orders.orders == []
