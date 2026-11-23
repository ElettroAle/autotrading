from autotrading.application.sources.errors import AssetRequiredError
from autotrading.application.sources.forecast_asset import ForecastAssetCommand, ForecastAssetUseCase
from autotrading.application.sources.ports import SourceRequest
from autotrading.domain.sources.forecast import HISTORY_DAYS, HORIZONS, LONG_HISTORY_DAYS
from autotrading.domain.sources.price_forecast import ForecastHorizon, PriceForecast
from autotrading.domain.sources.source_sample import SourceValue


class ReadForecastUseCase:
    """Forecasts the price of the asset at every horizon the flow chose; the data refers to the instant of the forecast
    (R1.3.5, R5.1.5, ADR parametri-delle-fonti-come-liste-libere). No horizon, no forecast and no value.
    """

    def __init__(self, forecast: ForecastAssetUseCase) -> None:
        self._forecast = forecast

    def execute(self, command: SourceRequest) -> tuple[SourceValue, ...]:
        if command.asset is None:
            raise AssetRequiredError
        horizons = tuple(ForecastHorizon(minutes) for minutes in HORIZONS.value_in(command.settings))
        if not horizons:
            return ()
        forecasts = self._forecast.execute(
            ForecastAssetCommand(
                command.flow_id,
                command.asset,
                HISTORY_DAYS.value_in(command.settings),
                command.now,
                horizons,
                LONG_HISTORY_DAYS.value_in(command.settings),
            )
        )
        return (SourceValue(command.now, _values_of(forecasts)),)


def _values_of(forecasts: tuple[PriceForecast, ...]) -> dict[str, str]:
    values = {"prezzo_attuale": str(forecasts[0].last_price)}
    for forecast in forecasts:
        label = forecast.horizon.label
        values[f"prezzo_previsto_{label}"] = str(forecast.predicted_price)
        values[f"variazione_percentuale_{label}"] = str(forecast.change_percent)
    short = [forecast for forecast in forecasts if not forecast.horizon.on_daily_candles]
    long = [forecast for forecast in forecasts if forecast.horizon.on_daily_candles]
    # The depth of each history, from the first forecast made on it.
    if short:
        values |= _short_history_of(short[0])
    if long:
        values |= _long_history_of(long[0])
    return values


def _short_history_of(forecast: PriceForecast) -> dict[str, str]:
    values = {"profondita_storico_giorni": str(forecast.history_days)}
    if forecast.shortened:
        values["storico_ridotto"] = "lo storico dell'exchange è più corto di quello richiesto"
    return values


def _long_history_of(forecast: PriceForecast) -> dict[str, str]:
    values = {"profondita_storico_lunga_giorni": str(forecast.history_days)}
    if forecast.shortened:
        values["storico_lungo_ridotto"] = "lo storico giornaliero dell'exchange è più corto di quello richiesto"
    return values
