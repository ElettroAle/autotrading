from decimal import Decimal

import pytest

from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.market import Market
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.slippage import Slippage


def test_an_opening_order_is_not_reduce_only_and_has_its_own_identifier() -> None:
    first = MarketOrder.opening("BTC", Direction.LONG, Decimal("0.001"), Slippage.default())
    second = MarketOrder.opening("BTC", Direction.LONG, Decimal("0.001"), Slippage.default())

    assert not first.reduce_only
    assert first.id != second.id


@pytest.mark.parametrize(
    ("direction", "reduce_only", "is_buy"),
    [
        (Direction.LONG, False, True),
        (Direction.SHORT, False, False),
        (Direction.LONG, True, False),
        (Direction.SHORT, True, True),
    ],
)
def test_the_side_follows_direction_and_purpose(direction: Direction, reduce_only: bool, is_buy: bool) -> None:
    order = MarketOrder("BTC", direction, Decimal(1), Slippage.default(), reduce_only=reduce_only)

    assert order.is_buy is is_buy


def a_market(mid_price: Decimal) -> Market:
    return Market("BTC", 40, 5, mid_price, Decimal(10), price_significant_figures=5, price_decimals=1)


def test_a_sale_below_a_book_far_under_the_oracle_is_limited_from_the_oracle() -> None:
    # The testnet on 20/11/2026: the book at 60,350, the oracle near 61,930; 57,330 was refused as too far from it.
    order = MarketOrder("BTC", Direction.LONG, Decimal(1), Slippage.default(), reduce_only=True)

    assert order.limit_price(a_market(Decimal(60350)), Decimal(61930)) == Decimal(58834)


def test_a_sale_with_the_book_above_the_oracle_is_limited_from_the_book() -> None:
    order = MarketOrder.opening("BTC", Direction.SHORT, Decimal(1), Slippage.default())

    assert order.limit_price(a_market(Decimal(62000)), Decimal(61000)) == Decimal(58900)


def test_a_purchase_with_the_book_far_above_the_oracle_is_limited_from_the_oracle() -> None:
    order = MarketOrder.opening("BTC", Direction.LONG, Decimal(1), Slippage.default())

    assert order.limit_price(a_market(Decimal(62000)), Decimal(61000)) == Decimal(64050)


def test_a_purchase_with_the_book_below_the_oracle_is_limited_from_the_book() -> None:
    order = MarketOrder("BTC", Direction.SHORT, Decimal(1), Slippage.percent(Decimal(2)), reduce_only=True)

    assert order.limit_price(a_market(Decimal(60350)), Decimal(61930)) == Decimal(61557)


def test_the_limit_is_rounded_to_a_price_the_exchange_admits() -> None:
    order = MarketOrder.opening("ETH", Direction.LONG, Decimal(1), Slippage.percent(Decimal(2)))
    market = Market("ETH", 25, 4, Decimal("4000.55"), Decimal(10), price_significant_figures=5, price_decimals=2)

    assert order.limit_price(market, Decimal("4100.11")) == Decimal("4080.6")
