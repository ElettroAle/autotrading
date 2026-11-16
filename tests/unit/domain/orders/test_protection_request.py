from decimal import Decimal

import pytest

from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.protection_request import ProtectionLevels, ProtectionRequest

ENTRY = Decimal(60000)
FIVE = Decimal(5)


def test_without_levels_of_the_agent_the_stop_is_the_default_distance_from_the_entry_price() -> None:
    request = ProtectionRequest(None, None, FIVE, None)

    assert request.levels_at(Direction.LONG, ENTRY) == ProtectionLevels(Decimal(57000), None, ())
    assert request.levels_at(Direction.SHORT, ENTRY) == ProtectionLevels(Decimal(63000), None, ())


def test_without_target_the_take_profit_is_the_default_distance_from_the_entry_price() -> None:
    request = ProtectionRequest(None, None, FIVE, Decimal(10))

    assert request.levels_at(Direction.LONG, ENTRY).take_profit == Decimal(66000)
    assert request.levels_at(Direction.SHORT, ENTRY).take_profit == Decimal(54000)


def test_the_levels_of_the_agent_win_over_the_defaults() -> None:
    request = ProtectionRequest(Decimal(58500), Decimal(63000), FIVE, Decimal(10))

    assert request.levels_at(Direction.LONG, ENTRY) == ProtectionLevels(Decimal(58500), Decimal(63000), ())


@pytest.mark.parametrize(
    ("direction", "stop", "default", "note"),
    [
        (
            Direction.LONG,
            Decimal(55000),
            Decimal(57000),
            "stop 55000 riportato a 57000: oltre lo stop predefinito del 5%",
        ),
        (
            Direction.SHORT,
            Decimal(64000),
            Decimal(63000),
            "stop 64000 riportato a 63000: oltre lo stop predefinito del 5%",
        ),
    ],
)
def test_a_stop_of_the_agent_beyond_the_default_goes_back_to_it_with_a_note(
    direction: Direction, stop: Decimal, default: Decimal, note: str
) -> None:
    levels = ProtectionRequest(stop, None, FIVE, None).levels_at(direction, ENTRY)

    assert (levels.stop, levels.notes) == (default, (note,))


def test_a_stop_of_the_agent_exactly_at_the_default_stays_without_note() -> None:
    assert ProtectionRequest(Decimal(57000), None, FIVE, None).levels_at(Direction.LONG, ENTRY).notes == ()


def test_a_decimal_default_reads_with_a_comma_in_the_note() -> None:
    levels = ProtectionRequest(Decimal(58000), None, Decimal("2.5"), None).levels_at(Direction.LONG, ENTRY)

    assert levels.notes == ("stop 58000 riportato a 58500: oltre lo stop predefinito del 2,5%",)
