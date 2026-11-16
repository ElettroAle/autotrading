"""The mean error of the forecasts of a flow by asset and horizon over a period (R3.6.1, ADR
errore-medio-della-previsione-nell-api).
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from autotrading.domain.flows.evaluated_forecast import EvaluatedForecast
from autotrading.domain.flows.forecast_accuracy import ForecastAccuracy
from autotrading.domain.flows.statistics_period import TimeWindow

EXPIRED = datetime(2026, 11, 16, 11, tzinfo=UTC)
WHOLE_LIFE = TimeWindow()


def forecast(
    predicted: str,
    actual: str | None = "60000",
    *,
    asset: str = "BTC",
    horizon: int = 60,
    expires_at: datetime = EXPIRED,
) -> EvaluatedForecast:
    return EvaluatedForecast(
        asset, horizon, expires_at, Decimal(predicted), None if actual is None else Decimal(actual)
    )


def test_the_means_are_over_the_evaluated_forecasts() -> None:
    (accuracy,) = ForecastAccuracy.per_asset_and_horizon(
        [forecast("60500", "60000"), forecast("61000", "61400")], WHOLE_LIFE
    )

    assert accuracy.mean_absolute_error == Decimal(450)
    assert accuracy.mean_percent_error == Decimal("0.74")
    assert (accuracy.evaluated, accuracy.unevaluable) == (2, 0)


def test_the_mean_percent_error_has_two_decimals() -> None:
    (accuracy,) = ForecastAccuracy.per_asset_and_horizon([forecast("60001", "60000")], WHOLE_LIFE)

    assert accuracy.mean_percent_error == Decimal("0.00")
    assert accuracy.mean_percent_error is not None
    assert accuracy.mean_percent_error.as_tuple().exponent == -2


def test_each_asset_and_horizon_has_its_own_error_in_order() -> None:
    accuracies = ForecastAccuracy.per_asset_and_horizon(
        [
            forecast("60900", horizon=60),
            forecast("60450", horizon=15),
            forecast("3030", "3000", asset="ETH", horizon=15),
        ],
        WHOLE_LIFE,
    )

    assert [(entry.asset, entry.horizon_minutes, entry.mean_absolute_error) for entry in accuracies] == [
        ("BTC", 15, Decimal(450)),
        ("BTC", 60, Decimal(900)),
        ("ETH", 15, Decimal(30)),
    ]


def test_a_forecast_without_actual_price_is_counted_apart() -> None:
    (accuracy,) = ForecastAccuracy.per_asset_and_horizon([forecast("60500"), forecast("60000", None)], WHOLE_LIFE)

    assert accuracy.mean_absolute_error == Decimal(500)
    assert (accuracy.evaluated, accuracy.unevaluable) == (1, 1)


def test_only_the_forecasts_expired_in_the_period_count() -> None:
    period = TimeWindow(EXPIRED - timedelta(days=1), EXPIRED + timedelta(days=1))

    (accuracy,) = ForecastAccuracy.per_asset_and_horizon(
        [forecast("60900", expires_at=EXPIRED - timedelta(days=5)), forecast("60300")], period
    )

    assert accuracy.mean_absolute_error == Decimal(300)
    assert accuracy.evaluated == 1


def test_an_asset_and_horizon_without_forecasts_in_the_period_has_no_mean() -> None:
    period = TimeWindow(since=EXPIRED + timedelta(days=1))

    (accuracy,) = ForecastAccuracy.per_asset_and_horizon([forecast("60500")], period)

    assert (accuracy.asset, accuracy.horizon_minutes) == ("BTC", 60)
    assert (accuracy.mean_absolute_error, accuracy.mean_percent_error) == (None, None)
    assert (accuracy.evaluated, accuracy.unevaluable) == (0, 0)


def test_only_unevaluable_forecasts_give_no_mean() -> None:
    (accuracy,) = ForecastAccuracy.per_asset_and_horizon([forecast("60500", None)], WHOLE_LIFE)

    assert (accuracy.mean_absolute_error, accuracy.mean_percent_error) == (None, None)
    assert (accuracy.evaluated, accuracy.unevaluable) == (0, 1)


def test_without_forecasts_there_is_no_error() -> None:
    assert ForecastAccuracy.per_asset_and_horizon([], WHOLE_LIFE) == ()
