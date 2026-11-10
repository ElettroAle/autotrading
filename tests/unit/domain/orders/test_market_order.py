from decimal import Decimal

import pytest

from autotrading.domain.orders.direction import Direction
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
