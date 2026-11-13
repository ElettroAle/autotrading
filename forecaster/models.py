"""The cache of the trained models: one per asset and history depth, shared by every flow that asks for it."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from forecaster.prophet_model import Forecast, PricePoint, TrainedModel

type Trainer = Callable[[list[PricePoint], TrainedModel | None], TrainedModel]
type Predictor = Callable[[TrainedModel, datetime], Forecast]


@dataclass(frozen=True, slots=True)
class ModelKey:
    asset: str
    history_days: int


class ForecastModels:
    """Retrains a model only when it is older than the interval, starting from its own parameters (§10, ADR 0107)."""

    def __init__(self, retraining: timedelta, trainer: Trainer, predictor: Predictor) -> None:
        self._retraining = retraining
        self._trainer = trainer
        self._predictor = predictor
        self._models: dict[ModelKey, TrainedModel] = {}

    def forecast(
        self, key: ModelKey, points: list[PricePoint], horizons: tuple[timedelta, ...]
    ) -> tuple[Forecast, ...]:
        model = self._current(key, points)
        last = points[-1].at
        return tuple(self._predictor(model, last + horizon) for horizon in horizons)

    def _current(self, key: ModelKey, points: list[PricePoint]) -> TrainedModel:
        cached = self._models.get(key)
        if cached is not None and points[-1].at - cached.trained_until < self._retraining:
            return cached
        model = self._trainer(points, cached)
        self._models[key] = model
        return model
