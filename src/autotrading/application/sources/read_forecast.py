from autotrading.application.sources.errors import AssetRequiredError
from autotrading.application.sources.forecast_asset import ForecastAssetCommand, ForecastAssetUseCase
from autotrading.application.sources.ports import SourceRequest
from autotrading.domain.sources.price_forecast import PriceForecast
from autotrading.domain.sources.source_sample import SourceValue

HISTORY_DAYS = "profondita_storico_giorni"


class ReadForecastUseCase:
    """Forecasts the price of the asset at every horizon; the data refers to the instant of the forecast (R1.3.5)."""

    def __init__(self, forecast: ForecastAssetUseCase) -> None:
        self._forecast = forecast

    def execute(self, command: SourceRequest) -> tuple[SourceValue]:
        if command.asset is None:
            raise AssetRequiredError
        forecasts = self._forecast.execute(
            ForecastAssetCommand(command.flow_id, command.asset, command.settings[HISTORY_DAYS], command.now)
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
    return values
