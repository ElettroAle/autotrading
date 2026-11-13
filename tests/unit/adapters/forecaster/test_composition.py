"""The forecaster adapter from the internal address of the service (ADR 0107)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import pytest

from autotrading.adapters.configuration.errors import MissingConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.forecaster.composition import forecaster_adapters
from autotrading.domain.sources.price_forecast import ForecastHorizon, PricePoint, history_of

NOW = datetime(2026, 11, 13, 10, 0, tzinfo=UTC)


def test_the_adapter_reaches_the_forecaster_at_its_address() -> None:
    urls: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        urls.append(str(request.url))
        return httpx.Response(200, json={"forecasts": [{"horizon_minutes": 15, "predicted_price": "1"}]})

    adapter = forecaster_adapters(
        ConfigurationSource({"FORECASTER_URL": "http://forecaster:8000"}), httpx.MockTransport(handle)
    )
    history = history_of([PricePoint(NOW - timedelta(minutes=age), Decimal(1)) for age in (2, 1, 0)], 1, NOW)
    adapter.predict("BTC", history, (ForecastHorizon.MINUTES_15,))

    assert urls == ["http://forecaster:8000/forecast"]


def test_without_the_address_the_worker_does_not_start() -> None:
    with pytest.raises(MissingConfigurationError):
        forecaster_adapters(ConfigurationSource({}))
