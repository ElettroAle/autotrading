from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from autotrading.application.sources.ports import ForecastRepositoryPort, PriceForecasterPort, PriceHistoryPort
from autotrading.domain.sources.price_forecast import ForecastHorizon, PriceForecast, PriceHistory, history_of


@dataclass(frozen=True, slots=True)
class ForecastAssetCommand:
    # None for a trial outside every flow: its forecast is never recorded (R6.3.1).
    flow_id: UUID | None
    asset: str
    history_days: int
    now: datetime
    # The horizons the flow chose (ADR parametri-delle-fonti-come-liste-libere), with the depth of the daily history of
    # those of a day or more (R5.1.5).
    horizons: tuple[ForecastHorizon, ...]
    long_history_days: int


class ForecastAssetUseCase:
    """Forecasts the price of an asset at every horizon from the history of the exchange, and records it for the flow
    that asked (R1.3.5); a trial asks for no flow and records nothing (R6.3.1).

    The history comes from the exchange, the prediction from the forecasting model (ADR 0107); the horizons of a day or
    more on the daily candles (ADR orizzonti-lunghi-del-forecast). A kind of history no horizon needs is not read.
    """

    def __init__(
        self, prices: PriceHistoryPort, forecaster: PriceForecasterPort, forecasts: ForecastRepositoryPort
    ) -> None:
        self._prices = prices
        self._forecaster = forecaster
        self._forecasts = forecasts

    def execute(self, command: ForecastAssetCommand) -> tuple[PriceForecast, ...]:
        forecasts = (*self._short_forecasts(command), *self._long_forecasts(command))
        if command.flow_id is not None:
            for forecast in forecasts:
                self._forecasts.add(forecast)
        return forecasts

    def _short_forecasts(self, command: ForecastAssetCommand) -> tuple[PriceForecast, ...]:
        horizons = tuple(horizon for horizon in command.horizons if not horizon.on_daily_candles)
        if not horizons:
            return ()
        points = self._prices.history(command.asset, command.history_days, command.now)
        return self._forecast(command, history_of(points, command.history_days, command.now), horizons)

    def _long_forecasts(self, command: ForecastAssetCommand) -> tuple[PriceForecast, ...]:
        horizons = tuple(horizon for horizon in command.horizons if horizon.on_daily_candles)
        if not horizons:
            return ()
        points = self._prices.daily_history(command.asset, command.long_history_days, command.now)
        return self._forecast(command, history_of(points, command.long_history_days, command.now), horizons)

    def _forecast(
        self, command: ForecastAssetCommand, history: PriceHistory, horizons: tuple[ForecastHorizon, ...]
    ) -> tuple[PriceForecast, ...]:
        predicted = self._forecaster.predict(command.asset, history, horizons)
        return tuple(
            PriceForecast.of(command.flow_id, command.asset, history, horizon, predicted[horizon])
            for horizon in horizons
        )
