from decimal import Decimal

import pytest

from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_order import ProtectionOrder


@pytest.mark.parametrize(("direction", "buys"), [(Direction.LONG, False), (Direction.SHORT, True)])
def test_a_protection_closes_its_position_selling_a_long_and_buying_a_short(direction: Direction, buys: bool) -> None:
    order = ProtectionOrder("BTC", ProtectionKind.STOP_LOSS, direction, Decimal(57000))

    assert order.is_buy is buys


def test_every_protection_has_its_own_client_order_id() -> None:
    first = ProtectionOrder("BTC", ProtectionKind.STOP_LOSS, Direction.LONG, Decimal(57000))
    second = ProtectionOrder("BTC", ProtectionKind.TAKE_PROFIT, Direction.LONG, Decimal(63000))

    assert first.client_order_id != second.client_order_id
