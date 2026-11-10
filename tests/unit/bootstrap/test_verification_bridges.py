"""The bridges bootstrap builds between the verification context and the accounts and orders contexts (ADR 0024)."""

from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.accounts.read_exchange_state import ReadExchangeStateUseCase
from autotrading.application.orders.close_exchange_position import CloseExchangePositionUseCase
from autotrading.application.orders.open_position import OpenPositionUseCase
from autotrading.application.verification.errors import VerificationAccountNotFoundError, VerificationStepError
from autotrading.bootstrap import AccountReadingFromAccounts, OrderExecutionFromOrders
from autotrading.domain.accounts.position import Position, PositionSide
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.order import OrderOrigin, OrderSource, OrderStatus
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from autotrading.domain.verification.procedure import PROCEDURE_OPENING
from autotrading.domain.verification.reading import AccountReading, PositionReading
from tests.fakes.account_repository import InMemoryAccountRepositoryAdapter
from tests.fakes.credential_opener import FakeCredentialOpenerAdapter
from tests.fakes.order_exchange import FakeOrderExchangeAdapter
from tests.fakes.order_repository import InMemoryOrderRepositoryAdapter
from tests.fakes.trading_access import FakeTradingAccessAdapter
from tests.support.trading import HYPERLIQUID, new_access
from tests.support.worker import Worker

ANNA = UserId("oid-anna")
VERIFICATION = OrderSource(OrderOrigin.VERIFICATION, "oid-anna")
SHORT_ETH = Position("ETH", PositionSide.SHORT, Decimal("1.5"), 3, Decimal(3000), Decimal("-4.2"), None)


class Orders:
    def __init__(self) -> None:
        self.exchange = FakeOrderExchangeAdapter()
        self.recorded = InMemoryOrderRepositoryAdapter()
        self.accesses = FakeTradingAccessAdapter()
        self.account_id = uuid4()
        self.accesses.accesses[self.account_id] = new_access()
        exchanges, slippage = {HYPERLIQUID: self.exchange}, Slippage.default()
        self.execution = OrderExecutionFromOrders(
            OpenPositionUseCase(self.accesses, exchanges, self.recorded, slippage),
            CloseExchangePositionUseCase(self.accesses, exchanges, self.recorded, slippage),
        )

    def hold_btc(self) -> None:
        position = HeldPosition("BTC", Direction.LONG, Decimal("0.00012"), 2)
        self.exchange.hold(self.accesses.accesses[self.account_id], position)


@pytest.fixture
def orders() -> Orders:
    return Orders()


def test_the_opening_is_long_btc_leverage_2_from_the_procedure_and_the_user(orders: Orders) -> None:
    result = orders.execution.open(orders.account_id, PROCEDURE_OPENING, ANNA)

    (order,) = orders.recorded.orders
    assert (order.request.source, order.request.leverage) == (VERIFICATION, 2)
    assert (order.request.market_order.coin, order.request.market_order.direction) == ("BTC", Direction.LONG)
    assert order.execution is not None
    assert (result.succeeded, result.fee, result.realized_pnl, result.message) == (
        True,
        order.execution.fee,
        Decimal(0),
        None,
    )


def test_the_closing_is_from_the_procedure_and_the_user(orders: Orders) -> None:
    orders.hold_btc()

    result = orders.execution.close(orders.account_id, "BTC", ANNA)

    (order,) = orders.recorded.orders
    assert order.request.source == VERIFICATION
    assert order.request.market_order.reduce_only
    assert (result.succeeded, result.realized_pnl) == (True, Decimal("1.75"))


def test_a_partly_executed_order_is_a_succeeded_step(orders: Orders) -> None:
    orders.exchange.fill_ratio = Decimal("0.5")

    result = orders.execution.open(orders.account_id, PROCEDURE_OPENING, ANNA)

    assert orders.recorded.orders[0].status is OrderStatus.PARTIALLY_FILLED
    assert result.succeeded


def test_a_refused_order_fails_with_the_message_of_the_exchange(orders: Orders) -> None:
    orders.exchange.rejection = "Insufficient margin to place order. asset=0"

    result = orders.execution.open(orders.account_id, PROCEDURE_OPENING, ANNA)

    assert (result.succeeded, result.fee, result.message) == (
        False,
        Decimal(0),
        "Insufficient margin to place order. asset=0",
    )


def test_an_order_without_outcome_fails_saying_so(orders: Orders) -> None:
    orders.exchange.silent = True

    result = orders.execution.open(orders.account_id, PROCEDURE_OPENING, ANNA)

    assert (result.succeeded, result.message) == (False, "esito sconosciuto")


def test_closing_without_a_position_fails_with_the_reason(orders: Orders) -> None:
    with pytest.raises(VerificationStepError) as raised:
        orders.execution.close(orders.account_id, "BTC", ANNA)

    assert raised.value.message == "nessuna posizione aperta su BTC"


def test_an_unreachable_exchange_fails_with_the_reason(orders: Orders) -> None:
    orders.exchange.reachable = False

    with pytest.raises(VerificationStepError) as raised:
        orders.execution.open(orders.account_id, PROCEDURE_OPENING, ANNA)

    assert raised.value.message == "exchange non raggiungibile, riprovare"


def test_an_opening_on_an_account_the_tenant_does_not_have_is_not_found(orders: Orders) -> None:
    with pytest.raises(VerificationAccountNotFoundError):
        orders.execution.open(uuid4(), PROCEDURE_OPENING, ANNA)


def test_a_closing_on_an_account_the_tenant_does_not_have_is_not_found(orders: Orders) -> None:
    with pytest.raises(VerificationAccountNotFoundError):
        orders.execution.close(uuid4(), "BTC", ANNA)


def readings_of(worker: Worker, tenant_id: TenantId) -> AccountReadingFromAccounts:
    accounts = InMemoryAccountRepositoryAdapter(worker.store, tenant_id)
    opener = FakeCredentialOpenerAdapter(worker.vault)
    return AccountReadingFromAccounts(ReadExchangeStateUseCase(accounts, opener, {HYPERLIQUID: worker.exchange}))


def test_the_reading_carries_balance_margin_and_positions() -> None:
    worker = Worker()
    account = worker.saved_account()
    worker.exchange.open_position(worker.vault[account.credentials.ciphertext][2], SHORT_ETH)

    reading = readings_of(worker, account.tenant_id).read(account.id.value)

    assert reading == AccountReading(
        Decimal("250.5"), Decimal("250.5"), "USDC", (PositionReading("ETH", "short", Decimal("1.5"), 3),)
    )


def test_a_reading_of_an_account_of_another_tenant_is_not_found() -> None:
    worker = Worker()
    theirs = worker.saved_account(TenantId.new())

    with pytest.raises(VerificationAccountNotFoundError):
        readings_of(worker, TenantId.new()).read(theirs.id.value)


def test_a_reading_that_fails_keeps_the_reason() -> None:
    worker = Worker()
    account = worker.saved_account()
    worker.exchange.reachable = False

    with pytest.raises(VerificationStepError) as raised:
        readings_of(worker, account.tenant_id).read(account.id.value)

    assert raised.value.message == "exchange non raggiungibile, riprovare"
