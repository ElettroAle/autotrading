from decimal import Decimal

import pytest

from autotrading.domain.sources.pivot_levels import DailyRange, NearestLevel, PivotLevels, PricePosition

# The previous UTC day of the requirement: high 110, low 90, close 100 (R1.3.4).
LEVELS = PivotLevels.of(DailyRange(high=Decimal(110), low=Decimal(90), close=Decimal(100)))


def test_the_levels_follow_the_classic_formula() -> None:
    assert PivotLevels(pp=Decimal(100), r1=Decimal(110), r2=Decimal(120), s1=Decimal(90), s2=Decimal(80)) == LEVELS
    assert [name for name, _ in LEVELS.named] == ["S2", "S1", "PP", "R1", "R2"]


def test_a_price_above_the_pivot_has_the_nearest_levels_on_both_sides() -> None:
    reading = LEVELS.reading_at(Decimal(105))

    assert reading.position is PricePosition.ABOVE
    assert reading.resistance is not None
    assert reading.support is not None
    assert (reading.resistance.name, round(reading.resistance.distance_percent, 2)) == ("R1", Decimal("4.76"))
    assert (reading.support.name, round(reading.support.distance_percent, 2)) == ("PP", Decimal("4.76"))


def test_a_price_below_the_pivot() -> None:
    reading = LEVELS.reading_at(Decimal(95))

    assert reading.position is PricePosition.BELOW
    assert (reading.resistance, reading.support) == (
        NearestLevel("PP", Decimal(100), Decimal(5) / Decimal(95) * 100),
        NearestLevel("S1", Decimal(90), Decimal(5) / Decimal(95) * 100),
    )


def test_a_price_beyond_the_last_resistance_has_none_above() -> None:
    reading = LEVELS.reading_at(Decimal(125))

    assert reading.resistance is None
    assert reading.support == NearestLevel("R2", Decimal(120), Decimal(4))


def test_a_price_below_the_last_support_has_none_below() -> None:
    reading = LEVELS.reading_at(Decimal(70))

    assert reading.support is None
    assert reading.resistance is not None
    assert reading.resistance.name == "S2"


@pytest.mark.parametrize(("price", "support", "resistance"), [(Decimal(100), "PP", "R1"), (Decimal(110), "R1", "R2")])
def test_a_price_on_a_level_takes_it_as_support_and_the_next_as_resistance(
    price: Decimal, support: str, resistance: str
) -> None:
    reading = LEVELS.reading_at(price)

    assert reading.support is not None
    assert reading.resistance is not None
    assert (reading.support.name, reading.support.distance_percent) == (support, Decimal(0))
    assert reading.resistance.name == resistance


def test_a_price_on_the_pivot_is_neither_above_nor_below() -> None:
    assert LEVELS.reading_at(Decimal(100)).position is PricePosition.ON
