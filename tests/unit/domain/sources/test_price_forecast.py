from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest

from autotrading.domain.sources.errors import (
    InsufficientHistoryError,
    InvalidForecastHorizonError,
    InvalidPriceForecastError,
)
from autotrading.domain.sources.price_forecast import (
    ForecastHorizon,
    PriceForecast,
    PriceHistory,
    PricePoint,
    history_of,
)

NOW = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
FLOW = uuid4()


def rising(days: int, spacing: timedelta = timedelta(hours=1), last: str = "100") -> list[PricePoint]:
    """One point per spacing up to now, rising by one unit per point and ending at the last price."""
    count = int(timedelta(days=days) / spacing)
    return [PricePoint(NOW - spacing * (count - index), Decimal(last) - (count - index)) for index in range(count + 1)]


BASE = PriceForecast(FLOW, "BTC", ForecastHorizon(15), NOW, Decimal(100), Decimal(101), 7, False)


def forecast(**changes: Any) -> PriceForecast:
    return replace(BASE, **changes)


@pytest.mark.parametrize(
    ("minutes", "label"),
    [
        (15, "15 minuti"),
        (90, "90 minuti"),
        (60, "1 ora"),
        (240, "4 ore"),
        (1440, "1 giorno"),
        (2160, "36 ore"),
        (4320, "3 giorni"),
        (10080, "1 settimana"),
        (20160, "2 settimane"),
        (43200, "30 giorni"),
    ],
)
def test_a_horizon_is_named_by_its_largest_whole_unit(minutes: int, label: str) -> None:
    assert ForecastHorizon(minutes).label == label


def test_a_horizon_lasts_its_minutes() -> None:
    assert ForecastHorizon(240).length == timedelta(hours=4)


@pytest.mark.parametrize(("minutes", "daily"), [(15, False), (1439, False), (1440, True), (2160, True)])
def test_a_horizon_of_a_day_or_more_is_forecast_on_the_daily_candles(minutes: int, daily: bool) -> None:
    assert ForecastHorizon(minutes).on_daily_candles is daily


@pytest.mark.parametrize("minutes", [0, -15])
def test_a_horizon_of_no_minutes_is_a_defect(minutes: int) -> None:
    with pytest.raises(InvalidForecastHorizonError) as raised:
        ForecastHorizon(minutes)

    assert (raised.value.minutes, raised.value.status_code) == (minutes, 500)


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


@pytest.mark.parametrize("horizon", [ForecastHorizon(15), ForecastHorizon(60), ForecastHorizon(1440)])
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
    made = PriceForecast.of(FLOW, "BTC", history_of(rising(3), 30, NOW), ForecastHorizon(60), Decimal(101))

    assert (made.history_days, made.shortened) == (3, True)


def test_the_predicted_price_keeps_two_more_decimals_than_the_last_price() -> None:
    history = history_of(rising(7, last="100.5"), 7, NOW)

    made = PriceForecast.of(FLOW, "BTC", history, ForecastHorizon(15), Decimal("100.123456"))

    assert made.predicted_price == Decimal("100.123")


def test_the_change_is_a_percentage_of_the_last_price_with_two_decimals() -> None:
    assert forecast(predicted_price=Decimal("101.2345")).change_percent == Decimal("1.23")


def test_a_falling_forecast_has_a_negative_change() -> None:
    assert forecast(predicted_price=Decimal(99)).change_percent == Decimal("-1.00")


def test_the_forecast_expires_after_its_horizon() -> None:
    assert forecast(horizon=ForecastHorizon(60)).expires_at == NOW + timedelta(hours=1)


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
        PriceForecast.of(FLOW, "BTC", history, ForecastHorizon(15), Decimal(101))


def test_a_daily_history_shorter_than_requested_declares_the_days_it_covers() -> None:
    history = history_of(rising(200, timedelta(days=1)), 365, NOW)

    assert (history.shortened, history.days) == (True, 200)


def test_a_long_forecast_expires_after_its_days() -> None:
    assert forecast(horizon=ForecastHorizon(10080)).expires_at == NOW + timedelta(days=7)
