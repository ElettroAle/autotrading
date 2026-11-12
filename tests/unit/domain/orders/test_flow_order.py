from decimal import Decimal

from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.flow_order import FlowClosing, FlowOpening, in_sending_order

BTC = FlowOpening("BTC", Direction.LONG, Decimal(100), 2)
SOL = FlowOpening("SOL", Direction.SHORT, Decimal(50), 1)


def test_closings_go_before_the_openings_keeping_their_relative_order() -> None:
    orders = (BTC, FlowClosing("ETH"), SOL, FlowClosing("DOGE"))

    assert in_sending_order(orders) == (FlowClosing("ETH"), FlowClosing("DOGE"), BTC, SOL)


def test_no_orders_give_no_orders() -> None:
    assert in_sending_order(()) == ()


def test_each_order_names_its_asset() -> None:
    assert (BTC.asset, FlowClosing("ETH").asset) == ("BTC", "ETH")
