from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from autotrading.application.sources.ports import ForecastRepositoryPort, PriceForecasterPort, PriceHistoryPort
from autotrading.domain.sources.price_forecast import ForecastHorizon, PriceForecast, history_of


@dataclass(frozen=True, slots=True)
class ForecastAssetCommand:
    # None for a trial outside every flow: its forecast is never recorded (R6.3.1).
    flow_id: UUID | None
    asset: str
    history_days: int
    now: datetime


class ForecastAssetUseCase:
    """Forecasts the price of an asset at every horizon from the history of the exchange, and records it for the flow
    that asked (R1.3.5); a trial asks for no flow and records nothing (R6.3.1).

    The history comes from the exchange, the prediction from the forecasting model (ADR 0107).
    """

    def __init__(
        self, prices: PriceHistoryPort, forecaster: PriceForecasterPort, forecasts: ForecastRepositoryPort
    ) -> None:
        self._prices = prices
        self._forecaster = forecaster
        self._forecasts = forecasts

    def execute(self, command: ForecastAssetCommand) -> tuple[PriceForecast, ...]:
        points = self._prices.history(command.asset, command.history_days, command.now)
        history = history_of(points, command.history_days, command.now)
        predicted = self._forecaster.predict(command.asset, history, tuple(ForecastHorizon))
        forecasts = tuple(
            PriceForecast.of(command.flow_id, command.asset, history, horizon, predicted[horizon])
            for horizon in ForecastHorizon
        )
        if command.flow_id is not None:
            for forecast in forecasts:
                self._forecasts.add(forecast)
        return forecasts
