from decimal import Decimal

from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.simulation.simulated_position import SimulatedPosition


def a_position(direction: Direction = Direction.LONG, leverage: int = 10) -> SimulatedPosition:
    return SimulatedPosition(
        coin="BTC",
        direction=direction,
        size=Decimal("0.01"),
        leverage=leverage,
        entry_price=Decimal(90000),
        margin=Decimal(90),
        maintenance_rate=Decimal("0.0125"),
    )


def test_long_liquidation_price_is_where_the_margin_left_meets_the_maintenance() -> None:
    position = a_position()

    price = position.liquidation_price

    equity = position.margin + (price - position.entry_price) * position.size
    assert abs(equity - position.maintenance_rate * price * position.size) < Decimal("0.0001")
    assert price < position.entry_price


def test_short_liquidation_price_is_above_the_entry() -> None:
    position = a_position(Direction.SHORT)

    price = position.liquidation_price

    equity = position.margin + (position.entry_price - price) * position.size
    assert abs(equity - position.maintenance_rate * price * position.size) < Decimal("0.0001")
    assert price > position.entry_price


def test_a_long_is_liquidated_once_the_price_reaches_the_liquidation_price() -> None:
    position = a_position()

    assert position.liquidated_at(position.liquidation_price)
    assert not position.liquidated_at(position.liquidation_price + 1)


def test_a_short_is_liquidated_once_the_price_reaches_the_liquidation_price() -> None:
    position = a_position(Direction.SHORT)

    assert position.liquidated_at(position.liquidation_price)
    assert not position.liquidated_at(position.liquidation_price - 1)


def test_unrealized_pnl_follows_the_direction() -> None:
    assert a_position().unrealized_pnl(Decimal(91000)) == Decimal(10)
    assert a_position(Direction.SHORT).unrealized_pnl(Decimal(91000)) == Decimal(-10)


def test_signed_size_is_negative_for_a_short() -> None:
    assert a_position().signed_size == Decimal("0.01")
    assert a_position(Direction.SHORT).signed_size == Decimal("-0.01")


def test_held_is_the_position_as_the_exchange_reports_it() -> None:
    assert a_position().held == HeldPosition("BTC", Direction.LONG, Decimal("0.01"), 10, Decimal(90000))


def test_a_position_never_read_again_is_shown_at_its_entry() -> None:
    assert a_position().mark == Decimal(90000)


def test_a_position_is_shown_at_the_last_price_read() -> None:
    position = SimulatedPosition(
        "BTC", Direction.LONG, Decimal(1), 2, Decimal(90000), Decimal(1), Decimal("0.01"), Decimal(91000)
    )

    assert position.mark == Decimal(91000)
