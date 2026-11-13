from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.application.sources.forecast_asset import ForecastAssetCommand, ForecastAssetUseCase
from autotrading.domain.sources.price_forecast import ForecastHorizon
from tests.fakes.forecast_repository import InMemoryForecastRepositoryAdapter
from tests.fakes.price_forecaster import FakePriceForecasterAdapter
from tests.fakes.price_history import FakePriceHistoryAdapter

NOW = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
FLOW = uuid4()


def test_the_asset_is_forecast_at_every_horizon_and_recorded() -> None:
    prices = FakePriceHistoryAdapter(prices={"BTC": Decimal(100)})
    forecaster = FakePriceForecasterAdapter()
    forecasts = InMemoryForecastRepositoryAdapter()

    made = ForecastAssetUseCase(prices, forecaster, forecasts).execute(ForecastAssetCommand(FLOW, "BTC", 7, NOW))

    assert [
        (forecast.horizon, forecast.last_price, forecast.predicted_price, forecast.history_days) for forecast in made
    ] == [
        (ForecastHorizon.MINUTES_15, Decimal(100), Decimal("100.15"), 7),
        (ForecastHorizon.HOUR_1, Decimal(100), Decimal("100.60"), 7),
    ]
    assert forecasts.forecasts == list(made)
    assert prices.requests == [("BTC", 7)]
    assert forecaster.requests == [("BTC", 7, (ForecastHorizon.MINUTES_15, ForecastHorizon.HOUR_1))]


def test_a_shorter_history_is_declared_by_every_forecast() -> None:
    prices = FakePriceHistoryAdapter(available_days=3)

    made = ForecastAssetUseCase(prices, FakePriceForecasterAdapter(), InMemoryForecastRepositoryAdapter()).execute(
        ForecastAssetCommand(FLOW, "BTC", 30, NOW)
    )

    assert {(forecast.history_days, forecast.shortened) for forecast in made} == {(3, True)}


def test_an_exchange_without_answer_records_nothing() -> None:
    forecasts = InMemoryForecastRepositoryAdapter()

    with pytest.raises(SourceUnavailableError):
        ForecastAssetUseCase(FakePriceHistoryAdapter(missing={"BTC"}), FakePriceForecasterAdapter(), forecasts).execute(
            ForecastAssetCommand(FLOW, "BTC", 7, NOW)
        )

    assert forecasts.forecasts == []


def test_a_forecaster_without_answer_records_nothing() -> None:
    forecasts = InMemoryForecastRepositoryAdapter()

    with pytest.raises(SourceUnavailableError):
        ForecastAssetUseCase(FakePriceHistoryAdapter(), FakePriceForecasterAdapter(missing={"BTC"}), forecasts).execute(
            ForecastAssetCommand(FLOW, "BTC", 7, NOW)
        )

    assert forecasts.forecasts == []
