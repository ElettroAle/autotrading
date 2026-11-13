import httpx

from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.forecaster.configuration import _settings_of
from autotrading.adapters.outbound.forecaster.price_forecast import ForecasterPriceForecastAdapter


def forecaster_adapters(
    source: ConfigurationSource, transport: httpx.BaseTransport | None = None
) -> ForecasterPriceForecastAdapter:
    """The forecasts of the forecaster service on the internal network of the installation (ADR 0107)."""
    settings = _settings_of(source)
    return ForecasterPriceForecastAdapter(
        httpx.Client(base_url=settings.url, timeout=settings.timeout_seconds, transport=transport)
    )
