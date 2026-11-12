from decimal import Decimal

import pytest

from autotrading.domain.sources.errors import InsufficientHistoryError
from autotrading.domain.sources.holt_forecast import MINIMUM_POINTS, holt_forecast


def prices(*values: int) -> list[Decimal]:
    return [Decimal(value) for value in values]


def test_a_steady_trend_is_extended_by_the_number_of_steps() -> None:
    assert holt_forecast(prices(100, 102, 104, 106, 108), Decimal(3)) == Decimal("114.0")


def test_a_fraction_of_a_step_moves_the_price_by_that_fraction_of_the_trend() -> None:
    assert holt_forecast(prices(100, 102, 104, 106, 108), Decimal("0.5")) == Decimal("109.0")


def test_a_flat_series_forecasts_the_same_price() -> None:
    assert holt_forecast(prices(50, 50, 50, 50), Decimal(4)) == Decimal("50.0")


def test_the_smoothing_follows_a_change_of_direction() -> None:
    falling_after_rise = prices(100, 110, 120, 130, 120, 110, 100, 90)

    assert holt_forecast(falling_after_rise, Decimal(1)) < Decimal(90)


def test_the_smoothing_is_chosen_by_the_smallest_one_step_error() -> None:
    # A noisy series: a high smoothing would chase the last point, the best pair stays close to the mean.
    noisy = prices(100, 104, 96, 104, 96, 104, 96, 104, 96, 104)

    assert Decimal(95) < holt_forecast(noisy, Decimal(1)) < Decimal(105)


def test_fewer_points_than_the_minimum_cannot_be_forecast() -> None:
    with pytest.raises(InsufficientHistoryError) as raised:
        holt_forecast(prices(100, 101), Decimal(1))

    assert (raised.value.needed, raised.value.available) == (MINIMUM_POINTS, 2)
