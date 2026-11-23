from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from forecaster.models import ForecastModels
from forecaster.prophet_model import Forecast, PricePoint, TrainedModel
from forecaster.service import create_application, retraining_interval

START = datetime(2026, 11, 1, tzinfo=UTC)
LAST = START + timedelta(minutes=6)


def fit(points: list[PricePoint], _warm_start: TrainedModel | None) -> TrainedModel:
    return TrainedModel("{}", points[-1].at)


def predict(_model: TrainedModel, _at: datetime) -> Forecast:
    return Forecast(Decimal("101.25"), Decimal("100.5"), Decimal("102"))


def client(models: ForecastModels | None = None) -> TestClient:
    return TestClient(create_application(models or ForecastModels(timedelta(minutes=15), fit, predict)))


def request(points: int = 3) -> dict[str, object]:
    return {
        "asset": "BTC",
        "history_days": 7,
        "points": [
            {"at": (START + timedelta(minutes=3 * index)).isoformat(), "price": "100"} for index in range(points)
        ],
        "horizons_minutes": [15, 60],
    }


def test_the_forecast_has_the_predicted_price_and_its_interval_for_every_horizon() -> None:
    response = client().post("/forecast", json=request())

    assert response.status_code == 200
    assert response.json() == {
        "forecasts": [
            {"horizon_minutes": 15, "predicted_price": "101.25", "lower_price": "100.5", "upper_price": "102"},
            {"horizon_minutes": 60, "predicted_price": "101.25", "lower_price": "100.5", "upper_price": "102"},
        ]
    }


def daily_request(horizons_minutes: list[int]) -> dict[str, object]:
    return {
        "asset": "BTC",
        "history_days": 365,
        # Daily closes ending at the last point of the finest candles of request(): only the key tells them apart.
        "points": [{"at": (LAST - timedelta(days=age)).isoformat(), "price": "100"} for age in (2, 1, 0)],
        "horizons_minutes": horizons_minutes,
        "daily_candles": True,
    }


def test_the_horizons_of_the_daily_candles_are_forecast_from_their_last_day() -> None:
    asked: list[datetime] = []

    def predict_at(_model: TrainedModel, at: datetime) -> Forecast:
        asked.append(at)
        return predict(_model, at)

    response = client(ForecastModels(timedelta(minutes=15), fit, predict_at)).post(
        "/forecast", json=daily_request([1440, 2160])
    )

    assert [entry["horizon_minutes"] for entry in response.json()["forecasts"]] == [1440, 2160]
    assert asked == [LAST + timedelta(days=1), LAST + timedelta(hours=36)]


def test_the_daily_model_of_an_asset_is_apart_from_the_one_of_the_finest_candles() -> None:
    trained: list[int] = []

    def fit_counting(points: list[PricePoint], warm_start: TrainedModel | None) -> TrainedModel:
        trained.append(len(points))
        return fit(points, warm_start)

    service = client(ForecastModels(timedelta(minutes=15), fit_counting, predict))
    daily = daily_request([1440]) | {"history_days": 7}
    service.post("/forecast", json=request())
    service.post("/forecast", json=daily)

    assert len(trained) == 2


@pytest.mark.parametrize("horizons", [{"horizons_minutes": []}, {}])
def test_a_request_without_horizons_is_refused(horizons: dict[str, list[int]]) -> None:
    body = {key: value for key, value in request().items() if key != "horizons_minutes"} | horizons

    assert client().post("/forecast", json=body).status_code == 422


def test_a_history_shorter_than_three_points_is_refused() -> None:
    assert client().post("/forecast", json=request(points=2)).status_code == 422


def test_the_health_answers_when_the_service_is_up() -> None:
    assert client().get("/health").json() == {"status": "ok"}


def test_the_retraining_interval_is_read_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FORECASTER_RETRAIN_MINUTES", "30")

    assert retraining_interval() == timedelta(minutes=30)


def test_the_retraining_interval_defaults_to_fifteen_minutes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FORECASTER_RETRAIN_MINUTES", raising=False)

    assert retraining_interval() == timedelta(minutes=15)
