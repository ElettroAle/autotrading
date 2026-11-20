from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest

from autotrading.domain.sources.errors import InsufficientHistoryError, InvalidPriceForecastError
from autotrading.domain.sources.price_forecast import (
    LONG_HORIZONS,
    SHORT_HORIZONS,
    ForecastHorizon,
    PriceForecast,
    PriceHistory,
    PricePoint,
    history_of,
    long_horizons_of,
)

NOW = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
FLOW = uuid4()


def rising(days: int, spacing: timedelta = timedelta(hours=1), last: str = "100") -> list[PricePoint]:
    """One point per spacing up to now, rising by one unit per point and ending at the last price."""
    count = int(timedelta(days=days) / spacing)
    return [PricePoint(NOW - spacing * (count - index), Decimal(last) - (count - index)) for index in range(count + 1)]


BASE = PriceForecast(FLOW, "BTC", ForecastHorizon.MINUTES_15, NOW, Decimal(100), Decimal(101), 7, False)


def forecast(**changes: Any) -> PriceForecast:
    return replace(BASE, **changes)


def test_the_horizons_are_15_minutes_1_hour_1_day_and_1_week() -> None:
    assert [(horizon.length, horizon.label) for horizon in ForecastHorizon] == [
        (timedelta(minutes=15), "15 minuti"),
        (timedelta(hours=1), "1 ora"),
        (timedelta(days=1), "1 giorno"),
        (timedelta(weeks=1), "1 settimana"),
    ]


def test_the_short_horizons_are_always_forecast_on_the_finest_candles() -> None:
    assert [(horizon, horizon.on_daily_candles) for horizon in SHORT_HORIZONS] == [
        (ForecastHorizon.MINUTES_15, False),
        (ForecastHorizon.HOUR_1, False),
    ]


def test_the_long_horizons_are_forecast_on_the_daily_candles_in_days() -> None:
    assert [(horizon.on_daily_candles, horizon.days) for horizon in LONG_HORIZONS] == [(True, 1), (True, 7)]


@pytest.mark.parametrize(
    ("minutes", "horizons"),
    [(0, ()), (1440, (ForecastHorizon.DAY_1,)), (10080, (ForecastHorizon.WEEK_1,)), (60, ())],
)
def test_the_long_horizon_chosen_by_its_minutes_none_for_no_long_horizon(
    minutes: int, horizons: tuple[ForecastHorizon, ...]
) -> None:
    assert long_horizons_of(minutes) == horizons


def test_a_history_covering_the_requested_days_is_not_shortened() -> None:
    history = history_of(rising(7), 7, NOW)

    assert (history.shortened, history.days, history.last_price) == (False, 7, Decimal(100))


def test_a_history_missing_less_than_one_interval_is_not_shortened() -> None:
    history = history_of(rising(7)[1:], 7, NOW)

    assert (history.shortened, history.days) == (False, 7)


def test_a_history_shorter_than_requested_declares_the_days_it_covers() -> None:
    history = history_of(rising(3), 30, NOW)

    assert (history.shortened, history.days) == (True, 3)


def test_a_part_of_a_day_counts_as_a_whole_day() -> None:
    history = history_of(rising(3)[-50:], 30, NOW)

    assert (history.shortened, history.days) == (True, 3)


def test_the_points_are_put_in_time_order() -> None:
    points = rising(1)

    assert history_of(list(reversed(points)), 1, NOW).points == tuple(points)


def test_the_spacing_is_the_average_distance_between_points() -> None:
    assert history_of(rising(1, timedelta(minutes=3)), 1, NOW).spacing == timedelta(minutes=3)


def test_fewer_than_three_points_are_not_a_history() -> None:
    with pytest.raises(InsufficientHistoryError):
        PriceHistory(tuple(rising(1)[-2:]), 1, NOW)


@pytest.mark.parametrize("horizon", list(ForecastHorizon))
def test_the_forecast_carries_the_predicted_price_of_its_horizon(horizon: ForecastHorizon) -> None:
    made = PriceForecast.of(FLOW, "BTC", history_of(rising(7), 7, NOW), horizon, Decimal("101.25"))

    assert (made.horizon, made.made_at, made.last_price, made.predicted_price) == (
        horizon,
        NOW,
        Decimal(100),
        Decimal("101.25"),
    )
    assert (made.flow_id, made.asset, made.history_days, made.shortened, made.actual_price) == (
        FLOW,
        "BTC",
        7,
        False,
        None,
    )


def test_the_forecast_declares_a_shortened_history() -> None:
    made = PriceForecast.of(FLOW, "BTC", history_of(rising(3), 30, NOW), ForecastHorizon.HOUR_1, Decimal(101))

    assert (made.history_days, made.shortened) == (3, True)


def test_the_predicted_price_keeps_two_more_decimals_than_the_last_price() -> None:
    history = history_of(rising(7, last="100.5"), 7, NOW)

    made = PriceForecast.of(FLOW, "BTC", history, ForecastHorizon.MINUTES_15, Decimal("100.123456"))

    assert made.predicted_price == Decimal("100.123")


def test_the_change_is_a_percentage_of_the_last_price_with_two_decimals() -> None:
    assert forecast(predicted_price=Decimal("101.2345")).change_percent == Decimal("1.23")


def test_a_falling_forecast_has_a_negative_change() -> None:
    assert forecast(predicted_price=Decimal(99)).change_percent == Decimal("-1.00")


def test_the_forecast_expires_after_its_horizon() -> None:
    assert forecast(horizon=ForecastHorizon.HOUR_1).expires_at == NOW + timedelta(hours=1)


def test_the_actual_price_is_recorded_next_to_the_forecast() -> None:
    made = forecast()

    assert made.with_actual(Decimal(102)) == forecast(actual_price=Decimal(102))


def test_a_forecast_without_time_zone_is_rejected() -> None:
    with pytest.raises(InvalidPriceForecastError):
        forecast(made_at=NOW.replace(tzinfo=None))


@pytest.mark.parametrize("price", [Decimal(0), Decimal(-1)])
def test_a_last_price_not_positive_is_rejected(price: Decimal) -> None:
    with pytest.raises(InvalidPriceForecastError):
        forecast(last_price=price)


def test_a_last_price_that_is_not_a_number_cannot_be_forecast() -> None:
    history = PriceHistory((*rising(1)[:-1], PricePoint(NOW, Decimal("Infinity"))), 1, NOW)

    with pytest.raises(InvalidPriceForecastError):
        PriceForecast.of(FLOW, "BTC", history, ForecastHorizon.MINUTES_15, Decimal(101))


def test_a_daily_history_shorter_than_requested_declares_the_days_it_covers() -> None:
    history = history_of(rising(200, timedelta(days=1)), 365, NOW)

    assert (history.shortened, history.days) == (True, 200)


def test_a_long_forecast_expires_after_its_days() -> None:
    assert forecast(horizon=ForecastHorizon.WEEK_1).expires_at == NOW + timedelta(days=7)
