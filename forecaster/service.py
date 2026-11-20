"""The HTTP API of the forecaster on the internal network of the installation (docs/architecture.md:254)."""

import os
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import FastAPI
from pydantic import BaseModel, Field, model_validator

from forecaster import prophet_model
from forecaster.models import ForecastModels, ModelKey

DEFAULT_RETRAINING_MINUTES = "15"
# Prophet needs a trend and a change of it: fewer points describe no series.
MINIMUM_POINTS = 3
MINUTES_PER_DAY = 24 * 60


class PricePointBody(BaseModel):
    at: datetime
    price: Decimal = Field(gt=0)


class ForecastRequest(BaseModel):
    asset: str = Field(min_length=1)
    history_days: int = Field(ge=1)
    points: list[PricePointBody] = Field(min_length=MINIMUM_POINTS)
    # The short horizons on the finest candles, or the long ones in days on the daily candles: never both, as one
    # model learns one series (ADR orizzonti-lunghi-del-forecast).
    horizons_minutes: list[int] = Field(default_factory=list)
    horizons_days: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def _one_kind_of_horizons(self) -> ForecastRequest:
        if bool(self.horizons_minutes) == bool(self.horizons_days):
            # pydantic answers a ValueError of a validator with 422, naming the request.
            reason = "horizons_minutes or horizons_days, not both nor neither"
            raise ValueError(reason)
        return self

    @property
    def daily(self) -> bool:
        return bool(self.horizons_days)

    @property
    def minutes(self) -> list[int]:
        """Every horizon in minutes, as the answer names it."""
        return self.horizons_minutes + [days * MINUTES_PER_DAY for days in self.horizons_days]


class HorizonForecast(BaseModel):
    horizon_minutes: int
    predicted_price: Decimal
    lower_price: Decimal
    upper_price: Decimal


class ForecastResponse(BaseModel):
    forecasts: list[HorizonForecast]


def retraining_interval() -> timedelta:
    # Not a secret: the interval is plain configuration of the compose file.
    return timedelta(minutes=int(os.environ.get("FORECASTER_RETRAIN_MINUTES", DEFAULT_RETRAINING_MINUTES)))


def create_application(models: ForecastModels | None = None) -> FastAPI:
    forecasts = models or ForecastModels(retraining_interval(), prophet_model.fit, prophet_model.predict)
    application = FastAPI(title="forecaster", docs_url=None, redoc_url=None, openapi_url=None)

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.post("/forecast")
    def forecast(request: ForecastRequest) -> ForecastResponse:
        points = sorted(
            (prophet_model.PricePoint(point.at, point.price) for point in request.points), key=lambda p: p.at
        )
        horizons = tuple(timedelta(minutes=minutes) for minutes in request.minutes)
        results = forecasts.forecast(ModelKey(request.asset, request.history_days, request.daily), points, horizons)
        return ForecastResponse(
            forecasts=[
                HorizonForecast(
                    horizon_minutes=minutes,
                    predicted_price=result.predicted,
                    lower_price=result.lower,
                    upper_price=result.upper,
                )
                for minutes, result in zip(request.minutes, results, strict=True)
            ]
        )

    return application
