from decimal import Decimal

import pytest

from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.slippage import Slippage


@pytest.mark.parametrize(("direction", "is_buy"), [(Direction.LONG, False), (Direction.SHORT, True)])
def test_the_closing_order_takes_the_opposite_side_for_the_whole_size(direction: Direction, is_buy: bool) -> None:
    order = HeldPosition("ETH", direction, Decimal("1.25"), 3).closing_order(Slippage.default())

    assert (order.coin, order.size, order.reduce_only, order.is_buy) == ("ETH", Decimal("1.25"), True, is_buy)


def test_the_closing_order_carries_the_slippage_asked() -> None:
    slippage = Slippage.percent(Decimal(1))

    assert HeldPosition("BTC", Direction.LONG, Decimal(1), 2).closing_order(slippage).slippage == slippage
