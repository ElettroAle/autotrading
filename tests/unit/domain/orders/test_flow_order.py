from decimal import Decimal

from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.flow_order import FlowClosing, FlowOpening, FlowUpdate, in_sending_order
from autotrading.domain.orders.protection_request import ProtectionRequest

PROTECTION = ProtectionRequest(None, None, Decimal(5), None)
BTC = FlowOpening("BTC", Direction.LONG, Decimal(100), 2, PROTECTION)
SOL = FlowOpening("SOL", Direction.SHORT, Decimal(50), 1, PROTECTION)
XRP = FlowUpdate("XRP", ProtectionRequest(Decimal(2), None, Decimal(5), None), remove_target=False)


def test_closings_go_before_the_openings_keeping_their_relative_order() -> None:
    orders = (BTC, FlowClosing("ETH"), SOL, FlowClosing("DOGE"))

    assert in_sending_order(orders) == (FlowClosing("ETH"), FlowClosing("DOGE"), BTC, SOL)


def test_no_orders_give_no_orders() -> None:
    assert in_sending_order(()) == ()


def test_each_order_names_its_asset() -> None:
    assert (BTC.asset, FlowClosing("ETH").asset) == ("BTC", "ETH")


def test_the_updates_go_after_the_closings_and_before_the_openings() -> None:
    orders = (BTC, XRP, FlowClosing("ETH"))

    assert in_sending_order(orders) == (FlowClosing("ETH"), XRP, BTC)


def test_an_update_names_its_asset() -> None:
    assert XRP.asset == "XRP"
