from autotrading.application.sources.errors import AssetRequiredError
from autotrading.application.sources.forecast_asset import ForecastAssetCommand, ForecastAssetUseCase
from autotrading.application.sources.ports import SourceRequest
from autotrading.domain.sources.forecast import FORECAST, HISTORY_DAYS, LONG_HISTORY_DAYS, LONG_HORIZON
from autotrading.domain.sources.price_forecast import PriceForecast, long_horizons_of
from autotrading.domain.sources.source_sample import SourceValue


class ReadForecastUseCase:
    """Forecasts the price of the asset at every horizon; the data refers to the instant of the forecast (R1.3.5,
    R5.1.5).
    """

    def __init__(self, forecast: ForecastAssetUseCase) -> None:
        self._forecast = forecast

    def execute(self, command: SourceRequest) -> tuple[SourceValue]:
        if command.asset is None:
            raise AssetRequiredError
        settings = FORECAST.settings(command.settings)
        forecasts = self._forecast.execute(
            ForecastAssetCommand(
                command.flow_id,
                command.asset,
                settings[HISTORY_DAYS],
                command.now,
                long_horizons_of(settings[LONG_HORIZON]),
                settings[LONG_HISTORY_DAYS],
            )
        )
        return (SourceValue(command.now, _values_of(forecasts)),)


def _values_of(forecasts: tuple[PriceForecast, ...]) -> dict[str, str]:
    first = forecasts[0]
    values = {"prezzo_attuale": str(first.last_price), "profondita_storico_giorni": str(first.history_days)}
    for forecast in forecasts:
        label = forecast.horizon.label
        values[f"prezzo_previsto_{label}"] = str(forecast.predicted_price)
        values[f"variazione_percentuale_{label}"] = str(forecast.change_percent)
    if first.shortened:
        values["storico_ridotto"] = "lo storico dell'exchange è più corto di quello richiesto"
    # The long forecast, when the flow chose one, comes last, on its own daily history.
    last = forecasts[-1]
    if last.horizon.on_daily_candles:
        values |= _long_history_of(last)
    return values


def _long_history_of(forecast: PriceForecast) -> dict[str, str]:
    values = {"profondita_storico_lunga_giorni": str(forecast.history_days)}
    if forecast.shortened:
        values["storico_lungo_ridotto"] = "lo storico giornaliero dell'exchange è più corto di quello richiesto"
    return values
