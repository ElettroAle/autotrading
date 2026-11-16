"""The error of one forecast once its horizon expires (R3.6.1, ADR errore-medio-della-previsione-nell-api)."""

from datetime import UTC, datetime
from decimal import Decimal

from autotrading.domain.flows.evaluated_forecast import EvaluatedForecast

EXPIRED = datetime(2026, 11, 16, 11, tzinfo=UTC)


def forecast(predicted: str, actual: str | None) -> EvaluatedForecast:
    return EvaluatedForecast("BTC", 60, EXPIRED, Decimal(predicted), None if actual is None else Decimal(actual))


def test_the_absolute_error_is_the_distance_from_the_actual_price_in_either_direction() -> None:
    assert forecast("60500", "60000").absolute_error == Decimal(500)
    assert forecast("61000", "61400").absolute_error == Decimal(400)


def test_the_percent_error_is_the_absolute_error_over_the_actual_price() -> None:
    assert forecast("60600", "60000").percent_error == Decimal(1)


def test_a_forecast_with_its_actual_price_is_evaluable() -> None:
    assert forecast("60500", "60000").evaluable


def test_a_forecast_without_actual_price_is_not_evaluable_and_has_no_error() -> None:
    missing = forecast("60500", None)

    assert not missing.evaluable
    assert (missing.absolute_error, missing.percent_error) == (None, None)


def test_a_forecast_with_an_actual_price_of_nothing_is_not_evaluable() -> None:
    nothing = forecast("60500", "0")

    assert not nothing.evaluable
    assert (nothing.absolute_error, nothing.percent_error) == (None, None)
