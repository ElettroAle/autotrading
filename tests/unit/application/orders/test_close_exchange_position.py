from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.orders.cancel_protections import CancelProtectionsUseCase
from autotrading.application.orders.close_exchange_position import (
    CloseExchangePositionCommand,
    CloseExchangePositionUseCase,
)
from autotrading.application.orders.errors import NoOpenPositionError, OrderAccountNotFoundError
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.order import OrderOrigin, OrderSource, OrderStatus
from autotrading.domain.orders.placed_protection import PlacedProtection
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_order import ProtectionOrder
from autotrading.domain.orders.slippage import Slippage
from tests.fakes.order_exchange import FakeOrderExchangeAdapter
from tests.fakes.order_repository import InMemoryOrderRepositoryAdapter
from tests.fakes.protection_exchange import FakeProtectionExchangeAdapter
from tests.fakes.protection_repository import InMemoryProtectionRepositoryAdapter, ProtectionStore
from tests.fakes.trading_access import TENANT, FakeTradingAccessAdapter
from tests.support.trading import HYPERLIQUID, new_access

MANUAL = OrderSource(OrderOrigin.MANUAL, "oid-anna")
SLIPPAGE = Slippage.percent(Decimal(3))
SHORT_ETH = HeldPosition("ETH", Direction.SHORT, Decimal("1.5"), 4, Decimal(100))


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
def protection_exchange() -> FakeProtectionExchangeAdapter:
    return FakeProtectionExchangeAdapter()


@pytest.fixture
def protections() -> InMemoryProtectionRepositoryAdapter:
    return InMemoryProtectionRepositoryAdapter(ProtectionStore(), TENANT)


@pytest.fixture
def use_case(
    accesses: FakeTradingAccessAdapter,
    exchange: FakeOrderExchangeAdapter,
    orders: InMemoryOrderRepositoryAdapter,
    protection_exchange: FakeProtectionExchangeAdapter,
    protections: InMemoryProtectionRepositoryAdapter,
) -> CloseExchangePositionUseCase:
    cancel = CancelProtectionsUseCase(accesses.use_case, {HYPERLIQUID: protection_exchange}, protections)
    return CloseExchangePositionUseCase(accesses.use_case, {HYPERLIQUID: exchange}, orders, SLIPPAGE, cancel)


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


@pytest.fixture
def stop_loss_id(
    accesses: FakeTradingAccessAdapter,
    account_id: UUID,
    protection_exchange: FakeProtectionExchangeAdapter,
    protections: InMemoryProtectionRepositoryAdapter,
) -> str:
    """The stop loss a flow placed on the short ETH position, on the exchange and recorded."""
    order = ProtectionOrder("ETH", ProtectionKind.STOP_LOSS, Direction.SHORT, Decimal(105))
    order_id = protection_exchange.place(accesses.accesses[account_id], order)
    protections.add(
        PlacedProtection(account_id, uuid4(), "ETH", order.kind, order.trigger_price, order_id, order.client_order_id)
    )
    return order_id


def test_an_executed_closing_cancels_the_protections_of_the_position(
    use_case: CloseExchangePositionUseCase,
    account_id: UUID,
    stop_loss_id: str,
    protection_exchange: FakeProtectionExchangeAdapter,
    protections: InMemoryProtectionRepositoryAdapter,
) -> None:
    use_case.execute(CloseExchangePositionCommand(account_id, "ETH", MANUAL))

    assert protection_exchange.cancelled == [stop_loss_id]
    assert protections.placed(account_id, "ETH") == ()


@pytest.mark.usefixtures("stop_loss_id")
def test_a_refused_closing_keeps_the_protections_of_the_position(
    use_case: CloseExchangePositionUseCase,
    exchange: FakeOrderExchangeAdapter,
    account_id: UUID,
    protection_exchange: FakeProtectionExchangeAdapter,
    protections: InMemoryProtectionRepositoryAdapter,
) -> None:
    exchange.rejection = "Insufficient margin"

    use_case.execute(CloseExchangePositionCommand(account_id, "ETH", MANUAL))

    assert protection_exchange.cancelled == []
    assert len(protections.placed(account_id, "ETH")) == 1


def test_an_account_the_tenant_does_not_have_is_not_found(
    use_case: CloseExchangePositionUseCase, exchange: FakeOrderExchangeAdapter
) -> None:
    with pytest.raises(OrderAccountNotFoundError):
        use_case.execute(CloseExchangePositionCommand(uuid4(), "ETH", MANUAL))

    assert exchange.sent == []
