from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.errors import UnknownSimulatedProtectionError
from autotrading.domain.orders.market import Market
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_order import ProtectionOrder
from autotrading.domain.orders.simulation.simulated_account import SimulatedAccount
from autotrading.domain.orders.simulation.simulated_book import SimulatedBook, SimulatedProtection
from autotrading.domain.orders.simulation.simulated_execution import SimulatedExecution
from autotrading.domain.orders.simulation.simulated_position import SimulatedPosition
from autotrading.domain.orders.slippage import Slippage

AT = datetime(2026, 11, 22, 12, tzinfo=UTC)
ENGINE = SimulatedExecution(Slippage(Decimal("0.001")))
STOP = ProtectionOrder("BTC", ProtectionKind.STOP_LOSS, Direction.LONG, Decimal(88000))
TARGET = ProtectionOrder("BTC", ProtectionKind.TAKE_PROFIT, Direction.LONG, Decimal(95000))


def a_market(price: Decimal = Decimal(90000), coin: str = "BTC") -> Market:
    return Market(coin, 40, 5, price, Decimal(10), taker_fee_rate=Decimal("0.00045"))


def a_long(leverage: int = 2, coin: str = "BTC") -> SimulatedPosition:
    margin = Decimal("0.01") * Decimal(90000) / leverage
    return SimulatedPosition(coin, Direction.LONG, Decimal("0.01"), leverage, Decimal(90000), margin, Decimal("0.0125"))


def a_book(*positions: SimulatedPosition, protections: tuple[SimulatedProtection, ...] = ()) -> SimulatedBook:
    return SimulatedBook(SimulatedAccount(Decimal(1000), positions), protections=protections)


def test_the_leverage_of_an_asset_is_one_until_it_is_set() -> None:
    book = a_book()

    assert book.leverage_of("BTC") == 1
    assert book.with_leverage("BTC", 3).leverage_of("BTC") == 3


def test_the_leverage_of_an_asset_without_one_set_is_the_one_of_its_position() -> None:
    assert a_book(a_long(leverage=5)).leverage_of("BTC") == 5


def test_an_order_executes_with_the_leverage_set_and_marks_the_position() -> None:
    order = MarketOrder("BTC", Direction.LONG, Decimal("0.001"), Slippage.default())

    book, fill = a_book().with_leverage("BTC", 4).executed(ENGINE, a_market(), order, AT)

    position = book.account.position_of("BTC")
    assert position is not None
    assert position.leverage == 4
    assert position.mark == Decimal(90000)
    assert fill.size == Decimal("0.001")


def test_a_protection_waits_until_it_is_removed() -> None:
    book = a_book(a_long()).with_protection(SimulatedProtection("1", STOP))

    assert [protection.order_id for protection in book.active("BTC")] == ["1"]
    assert book.active("ETH") == ()
    assert book.without_protection("1").active("BTC") == ()


def test_a_protection_not_waiting_cannot_be_removed() -> None:
    with pytest.raises(UnknownSimulatedProtectionError):
        a_book().without_protection("1")


def test_the_settlement_closes_a_position_whose_stop_loss_the_price_reached() -> None:
    book = a_book(a_long(), protections=(SimulatedProtection("1", STOP), SimulatedProtection("2", TARGET)))

    settlement = book.settled(ENGINE, {"BTC": a_market(Decimal(88000))}, AT)

    assert settlement.book.account.position_of("BTC") is None
    assert settlement.book.protections == ()
    (settled,) = settlement.fills
    assert settled.client_order_id == STOP.client_order_id
    assert settled.fill.realized_pnl < 0
    assert settlement.book.account.balance == Decimal(1000) + settled.fill.realized_pnl - settled.fill.fee


def test_the_settlement_liquidates_a_position_beyond_its_liquidation_price() -> None:
    position = a_long(leverage=10)
    book = a_book(position, protections=(SimulatedProtection("1", STOP),))

    settlement = book.settled(ENGINE, {"BTC": a_market(position.liquidation_price - 1)}, AT)

    (settled,) = settlement.fills
    assert settled.fill.liquidation
    assert settled.client_order_id is None
    assert settlement.book.account.position_of("BTC") is None
    assert settlement.book.protections == ()


def test_the_settlement_marks_a_position_no_price_closes() -> None:
    settlement = a_book(a_long()).settled(ENGINE, {"BTC": a_market(Decimal(91000))}, AT)

    position = settlement.book.account.position_of("BTC")
    assert position is not None
    assert position.mark == Decimal(91000)
    assert settlement.book.account.value == Decimal(1010)
    assert settlement.fills == ()


def test_the_settlement_leaves_a_position_without_a_market_as_it_is() -> None:
    book = a_book(a_long())

    assert book.settled(ENGINE, {}, AT).book == book


def test_a_reset_closes_every_position_at_its_last_price_and_brings_the_balance() -> None:
    marked = replace(a_long(), mark_price=Decimal(89000))
    book = a_book(marked, protections=(SimulatedProtection("1", STOP),)).with_leverage("BTC", 3)

    reset = book.reset(Decimal(500), AT)

    (fill,) = reset.fills
    assert fill.price == Decimal(89000)
    assert fill.realized_pnl == Decimal(-10)
    assert fill.fee == 0
    assert not fill.is_buy
    assert reset.movement == Decimal(500) - (Decimal(1000) - Decimal(10))
    assert reset.book == SimulatedBook(SimulatedAccount(Decimal(500)))


def test_a_reset_of_a_short_buys_it_back() -> None:
    short = SimulatedPosition("BTC", Direction.SHORT, Decimal("0.01"), 2, Decimal(90000), Decimal(450), Decimal("0.01"))

    (fill,) = a_book(short).reset(Decimal(1000), AT).fills

    assert fill.is_buy
    assert fill.start_position == Decimal("-0.01")
