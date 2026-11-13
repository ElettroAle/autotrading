from datetime import UTC, datetime, timedelta
from decimal import Decimal

from forecaster.prophet_model import PricePoint, fit, predict

START = datetime(2026, 11, 1, tzinfo=UTC)
STEP = timedelta(minutes=3)


def rising_points(count: int = 400) -> list[PricePoint]:
    return [PricePoint(START + index * STEP, Decimal(100) + Decimal(index) / 100) for index in range(count)]


def test_the_forecast_follows_the_trend_of_the_history() -> None:
    points = rising_points()
    model = fit(points, warm_start=None)

    forecast = predict(model, points[-1].at + timedelta(hours=1))

    assert Decimal("103.9") < forecast.predicted < Decimal("104.4")
    assert forecast.lower <= forecast.predicted <= forecast.upper


def test_a_warm_start_from_a_previous_model_gives_the_same_trend() -> None:
    points = rising_points()
    previous = fit(points[:-20], warm_start=None)

    forecast = predict(fit(points, warm_start=previous), points[-1].at + timedelta(minutes=15))

    assert Decimal("103.8") < forecast.predicted < Decimal("104.2")
