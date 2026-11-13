"""The bridge bootstrap builds between the verification context and the orders context (ADR 0024)."""

from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.orders.close_exchange_position import CloseExchangePositionUseCase
from autotrading.application.orders.open_position import OpenPositionUseCase
from autotrading.application.orders.read_market import ReadMarketUseCase
from autotrading.application.verification.errors import VerificationAccountNotFoundError, VerificationStepError
from autotrading.bootstrap import OrderExecutionFromOrders
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.order import OrderOrigin, OrderSource, OrderStatus
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.tenancy.user_id import UserId
from autotrading.domain.verification.procedure import Opening
from tests.fakes.order_exchange import FakeOrderExchangeAdapter
from tests.fakes.order_repository import InMemoryOrderRepositoryAdapter
from tests.fakes.trading_access import FakeTradingAccessAdapter
from tests.support.trading import HYPERLIQUID, new_access

ANNA = UserId("oid-anna")
VERIFICATION = OrderSource(OrderOrigin.VERIFICATION, "oid-anna")
PROCEDURE_OPENING = Opening(coin="BTC", side="long", leverage=2, value=Decimal(12))


class Orders:
    def __init__(self) -> None:
        self.exchange = FakeOrderExchangeAdapter()
        self.recorded = InMemoryOrderRepositoryAdapter()
        self.accesses = FakeTradingAccessAdapter()
        self.account_id = uuid4()
        self.accesses.accesses[self.account_id] = new_access()
        exchanges, slippage = {HYPERLIQUID: self.exchange}, Slippage.default()
        self.execution = OrderExecutionFromOrders(
            OpenPositionUseCase(self.accesses.use_case, exchanges, self.recorded, slippage),
            CloseExchangePositionUseCase(self.accesses.use_case, exchanges, self.recorded, slippage),
            ReadMarketUseCase(self.accesses.use_case, exchanges),
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


def test_the_minimum_value_is_the_one_the_exchange_of_the_account_sets_on_the_asset(orders: Orders) -> None:
    orders.exchange.markets["BTC"] = replace(orders.exchange.markets["BTC"], min_order_value=Decimal("7.5"))

    assert orders.execution.minimum_value(orders.account_id, "BTC") == Decimal("7.5")
    assert orders.exchange.sent == []


def test_a_minimum_value_that_cannot_be_read_fails_with_the_reason(orders: Orders) -> None:
    orders.exchange.reachable = False

    with pytest.raises(VerificationStepError):
        orders.execution.minimum_value(orders.account_id, "BTC")


def test_a_minimum_value_on_an_account_the_tenant_does_not_have_is_not_found(orders: Orders) -> None:
    with pytest.raises(VerificationAccountNotFoundError):
        orders.execution.minimum_value(uuid4(), "BTC")


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
