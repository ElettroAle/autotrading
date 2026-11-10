from datetime import UTC, datetime
from decimal import Decimal

from autotrading.domain.accounts.account_state import AccountState
from autotrading.domain.accounts.balance import Balance
from autotrading.domain.accounts.position import Position, PositionSide


def test_the_sides_are_named_as_the_requirement_names_them() -> None:
    assert [side.value for side in PositionSide] == ["long", "short"]


def test_a_position_may_have_no_liquidation_price() -> None:
    position = Position("BTC", PositionSide.LONG, Decimal(1), 1, Decimal(10), Decimal(0), None)

    assert position.liquidation_price is None


def test_a_state_holds_its_positions_in_the_order_read() -> None:
    first = Position("BTC", PositionSide.LONG, Decimal(1), 2, Decimal(10), Decimal(1), Decimal(5))
    second = Position("ETH", PositionSide.SHORT, Decimal(2), 3, Decimal(20), Decimal(-1), Decimal(40))
    balance = Balance(Decimal(100), "USDC")

    state = AccountState(balance, balance, (first, second), datetime(2026, 11, 10, tzinfo=UTC))

    assert [position.coin for position in state.positions] == ["BTC", "ETH"]
