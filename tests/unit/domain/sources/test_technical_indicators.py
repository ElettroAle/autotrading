from decimal import Decimal

import pytest

from autotrading.domain.sources.errors import InsufficientHistoryError
from autotrading.domain.sources.technical_indicators import (
    MacdPoint,
    exponential_moving_average,
    last_values,
    macd,
    relative_strength_index,
    simple_moving_average,
)


def numbers(*values: int) -> list[Decimal]:
    return [Decimal(value) for value in values]


def ramp(count: int) -> list[Decimal]:
    return [Decimal(value) for value in range(1, count + 1)]


def test_the_simple_average_moves_one_value_at_a_time() -> None:
    assert simple_moving_average(numbers(1, 2, 3, 4, 5), 3) == numbers(2, 3, 4)


def test_the_exponential_average_starts_from_the_simple_one_then_smooths() -> None:
    assert exponential_moving_average(numbers(1, 2, 3, 4, 5), 3) == numbers(2, 3, 4)
    assert exponential_moving_average(numbers(2, 2, 2, 8), 3) == [Decimal(2), Decimal(5)]


def test_the_exponential_average_of_a_ramp_lags_by_half_its_period() -> None:
    # Seeded with the simple average, the EMA of a straight line stays exactly (period - 1) / 2 behind it.
    averages = exponential_moving_average(ramp(60), 20)

    assert averages == [Decimal(value) - Decimal("9.5") for value in range(20, 61)]


def test_the_macd_of_a_ramp_is_the_constant_gap_of_the_two_averages() -> None:
    points = macd(ramp(40))

    assert len(points) == 40 - (26 + 9 - 1) + 1
    assert set(points) == {MacdPoint(Decimal(7), Decimal(7), Decimal(0))}


def test_the_macd_of_still_prices_is_zero() -> None:
    assert set(macd([Decimal(50)] * 34)) == {MacdPoint(Decimal(0), Decimal(0), Decimal(0))}


def test_the_rsi_of_rising_prices_is_100_and_of_falling_prices_is_0() -> None:
    assert set(relative_strength_index(ramp(20), 14)) == {Decimal(100)}
    assert set(relative_strength_index(list(reversed(ramp(20))), 14)) == {Decimal(0)}


def test_the_rsi_of_still_prices_is_50() -> None:
    assert relative_strength_index([Decimal(10)] * 9, 7) == [Decimal(50), Decimal(50)]


def test_the_rsi_follows_wilder_smoothing() -> None:
    # Changes +1, -1: averages 0.5 and 0.5 (RSI 50); then +1: gain 0.75, loss 0.25, RS 3 (RSI 75).
    assert relative_strength_index(numbers(10, 11, 10, 11), 2) == [Decimal(50), Decimal(75)]


@pytest.mark.parametrize(
    ("compute", "needed"),
    [
        (lambda values: simple_moving_average(values, 20), 20),
        (lambda values: exponential_moving_average(values, 50), 50),
        (macd, 34),
        (lambda values: relative_strength_index(values, 14), 15),
    ],
)
def test_a_history_too_short_is_refused_with_what_is_needed(compute: object, needed: int) -> None:
    assert callable(compute)
    with pytest.raises(InsufficientHistoryError) as raised:
        compute(ramp(needed - 1))

    assert str(raised.value) == f"storico dei prezzi insufficiente: servono {needed} valori, disponibili {needed - 1}"


def test_the_last_values_are_the_most_recent_oldest_first() -> None:
    assert last_values(numbers(1, 2, 3, 4), 2) == numbers(3, 4)
    assert last_values(numbers(1, 2), 10) == numbers(1, 2)
