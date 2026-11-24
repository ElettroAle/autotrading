from datetime import UTC, datetime
from decimal import Decimal

from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.simulation.simulated_account import SimulatedAccount
from autotrading.domain.orders.simulation.simulated_fill import SimulatedFill
from autotrading.domain.orders.simulation.simulated_position import SimulatedPosition


def a_position(coin: str, margin: str) -> SimulatedPosition:
    return SimulatedPosition(coin, Direction.LONG, Decimal(1), 2, Decimal(100), Decimal(margin), Decimal("0.01"))


def test_the_margin_of_the_open_positions_is_not_available() -> None:
    account = SimulatedAccount(Decimal(1000), (a_position("BTC", "100"), a_position("ETH", "50")))

    assert account.available_margin == Decimal(850)


def test_a_position_is_found_by_its_coin() -> None:
    eth = a_position("ETH", "50")
    account = SimulatedAccount(Decimal(1000), (a_position("BTC", "100"), eth))

    assert account.position_of("ETH") == eth
    assert account.position_of("SOL") is None


def test_a_position_replaced_keeps_the_others() -> None:
    account = SimulatedAccount(Decimal(1000), (a_position("BTC", "100"), a_position("ETH", "50")))

    replaced = account.with_position("BTC", a_position("BTC", "10"))

    assert replaced.available_margin == Decimal(940)
    assert account.with_position("BTC", None).positions == (a_position("ETH", "50"),)


def test_a_movement_changes_the_balance() -> None:
    assert SimulatedAccount(Decimal(1000)).moved(Decimal(-12)).balance == Decimal(988)


def test_the_signed_size_of_a_fill_is_negative_for_a_sale() -> None:
    at = datetime(2026, 11, 22, tzinfo=UTC)
    sale = SimulatedFill("BTC", False, Decimal(1), Decimal(100), Decimal(0), Decimal(0), Decimal(1), False, at)

    assert sale.signed_size == Decimal(-1)


def test_the_value_adds_the_unrealized_pnl_at_the_last_price_and_the_available_margin_follows_it() -> None:
    marked = SimulatedPosition(
        "BTC", Direction.LONG, Decimal(1), 2, Decimal(100), Decimal(50), Decimal("0.01"), mark_price=Decimal(90)
    )
    account = SimulatedAccount(Decimal(1000), (marked,))

    assert account.unrealized_pnl == Decimal(-10)
    assert account.value == Decimal(990)
    assert account.available_margin == Decimal(940)
