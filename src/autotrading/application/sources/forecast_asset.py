from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from autotrading.application.sources.ports import ForecastRepositoryPort, PriceHistoryPort
from autotrading.domain.sources.price_forecast import ForecastHorizon, PriceForecast, history_of


@dataclass(frozen=True, slots=True)
class ForecastAssetCommand:
    flow_id: UUID
    asset: str
    history_days: int
    now: datetime


class ForecastAssetUseCase:
    """Forecasts the price of an asset at every horizon from the history of the exchange, and records it (R1.3.5)."""

    def __init__(self, prices: PriceHistoryPort, forecasts: ForecastRepositoryPort) -> None:
        self._prices = prices
        self._forecasts = forecasts

    def execute(self, command: ForecastAssetCommand) -> tuple[PriceForecast, ...]:
        points = self._prices.history(command.asset, command.history_days, command.now)
        history = history_of(points, command.history_days, command.now)
        forecasts = tuple(
            PriceForecast.of(command.flow_id, command.asset, history, horizon) for horizon in ForecastHorizon
        )
        for forecast in forecasts:
            self._forecasts.add(forecast)
        return forecasts
