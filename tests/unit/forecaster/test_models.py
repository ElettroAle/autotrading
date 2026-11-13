from datetime import UTC, datetime, timedelta
from decimal import Decimal

from forecaster.models import ForecastModels, ModelKey
from forecaster.prophet_model import Forecast, PricePoint, TrainedModel

START = datetime(2026, 11, 1, tzinfo=UTC)
KEY = ModelKey("BTC", 7)


class RecordingTrainer:
    """Counts the fits and remembers the warm start each one received."""

    def __init__(self) -> None:
        self.warm_starts: list[TrainedModel | None] = []

    def fit(self, points: list[PricePoint], warm_start: TrainedModel | None) -> TrainedModel:
        self.warm_starts.append(warm_start)
        return TrainedModel(f"model-{len(self.warm_starts)}", points[-1].at)

    @staticmethod
    def predict(model: TrainedModel, _at: datetime) -> Forecast:
        return Forecast(Decimal(len(model.json)), Decimal(0), Decimal(99))


def points_until(last: datetime) -> list[PricePoint]:
    return [PricePoint(last - timedelta(minutes=minutes), Decimal(100)) for minutes in (6, 3, 0)]


def models(trainer: RecordingTrainer) -> ForecastModels:
    return ForecastModels(timedelta(minutes=15), trainer.fit, trainer.predict)


def test_the_first_forecast_of_an_asset_trains_a_model_from_zero() -> None:
    trainer = RecordingTrainer()

    models(trainer).forecast(KEY, points_until(START), (timedelta(minutes=15),))

    assert trainer.warm_starts == [None]


def test_a_model_younger_than_the_retraining_interval_is_reused() -> None:
    trainer = RecordingTrainer()
    cache = models(trainer)
    cache.forecast(KEY, points_until(START), (timedelta(minutes=15),))

    cache.forecast(KEY, points_until(START + timedelta(minutes=14)), (timedelta(minutes=15),))

    assert len(trainer.warm_starts) == 1


def test_an_older_model_is_retrained_starting_from_its_parameters() -> None:
    trainer = RecordingTrainer()
    cache = models(trainer)
    cache.forecast(KEY, points_until(START), (timedelta(minutes=15),))

    cache.forecast(KEY, points_until(START + timedelta(minutes=15)), (timedelta(minutes=15),))

    assert trainer.warm_starts == [None, TrainedModel("model-1", START)]


def test_another_asset_or_depth_has_its_own_model() -> None:
    trainer = RecordingTrainer()
    cache = models(trainer)
    cache.forecast(KEY, points_until(START), (timedelta(minutes=15),))

    cache.forecast(ModelKey("BTC", 30), points_until(START), (timedelta(minutes=15),))
    cache.forecast(ModelKey("ETH", 7), points_until(START), (timedelta(minutes=15),))

    assert trainer.warm_starts == [None, None, None]


def test_every_horizon_is_forecast_from_the_last_point() -> None:
    trainer = RecordingTrainer()
    asked: list[datetime] = []

    def predict(model: TrainedModel, at: datetime) -> Forecast:
        asked.append(at)
        return trainer.predict(model, at)

    ForecastModels(timedelta(minutes=15), trainer.fit, predict).forecast(
        KEY, points_until(START), (timedelta(minutes=15), timedelta(hours=1))
    )

    assert asked == [START + timedelta(minutes=15), START + timedelta(hours=1)]
