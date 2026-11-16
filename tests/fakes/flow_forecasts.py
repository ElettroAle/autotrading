"""Fake of the forecasts as the flows context reads them: the forecasts one tenant recorded (R1.3.5, R3.6.1)."""

from datetime import datetime

from autotrading.domain.flows.evaluated_forecast import EvaluatedForecast
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.sources.price_forecast import PriceForecast
from tests.fakes.forecast_repository import InMemoryForecastRepositoryAdapter


class InMemoryFlowForecastsAdapter:
    """Reads the forecasts of one tenant, as the real adapter does under row level security."""

    def __init__(self, recorded: InMemoryForecastRepositoryAdapter) -> None:
        self._recorded = recorded

    def expired_forecasts(self, flow_id: FlowId, now: datetime) -> list[EvaluatedForecast]:
        return [
            _evaluated(forecast)
            for forecast in self._recorded.forecasts
            if forecast.flow_id == flow_id.value and forecast.expires_at <= now
        ]


def _evaluated(forecast: PriceForecast) -> EvaluatedForecast:
    return EvaluatedForecast(
        forecast.asset, forecast.horizon.minutes, forecast.expires_at, forecast.predicted_price, forecast.actual_price
    )
