import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.sources.record_actual_prices import RecordActualPricesCommand, RecordActualPricesUseCase
from autotrading.domain.sources.price_forecast import ForecastHorizon, PriceForecast
from tests.fakes.forecast_repository import InMemoryForecastRepositoryAdapter
from tests.fakes.price_history import FakePriceHistoryAdapter

TEN = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
FLOW = uuid4()


def made(asset: str, horizon: ForecastHorizon) -> PriceForecast:
    return PriceForecast(FLOW, asset, horizon, TEN, Decimal(100), Decimal(101), 7, False)


def repository_with(*forecasts: PriceForecast) -> InMemoryForecastRepositoryAdapter:
    repository = InMemoryForecastRepositoryAdapter()
    for forecast in forecasts:
        repository.add(forecast)
    return repository


def test_the_actual_price_is_recorded_once_the_horizon_expires() -> None:
    repository = repository_with(made("BTC", ForecastHorizon.MINUTES_15), made("BTC", ForecastHorizon.HOUR_1))
    prices = FakePriceHistoryAdapter(prices={"BTC": Decimal(102)})

    recorded = RecordActualPricesUseCase(prices, repository).execute(
        RecordActualPricesCommand(TEN + timedelta(minutes=15))
    )

    assert recorded == [made("BTC", ForecastHorizon.MINUTES_15).with_actual(Decimal(102))]
    assert [forecast.actual_price for forecast in repository.forecasts] == [Decimal(102), None]


def test_a_forecast_already_completed_is_not_recorded_again() -> None:
    repository = repository_with(made("BTC", ForecastHorizon.MINUTES_15).with_actual(Decimal(102)))

    recorded = RecordActualPricesUseCase(FakePriceHistoryAdapter(prices={"BTC": Decimal(110)}), repository).execute(
        RecordActualPricesCommand(TEN + timedelta(hours=2))
    )

    assert recorded == []
    assert repository.forecasts[0].actual_price == Decimal(102)


def test_an_asset_without_price_waits_for_the_next_run(caplog: pytest.LogCaptureFixture) -> None:
    repository = repository_with(made("BTC", ForecastHorizon.MINUTES_15), made("ETH", ForecastHorizon.MINUTES_15))
    prices = FakePriceHistoryAdapter(prices={"ETH": Decimal(3000)}, missing={"BTC"})

    with caplog.at_level(logging.WARNING, logger="autotrading.sources"):
        recorded = RecordActualPricesUseCase(prices, repository).execute(
            RecordActualPricesCommand(TEN + timedelta(minutes=15))
        )

    assert [(forecast.asset, forecast.actual_price) for forecast in recorded] == [("ETH", Decimal(3000))]
    assert [forecast.actual_price for forecast in repository.forecasts] == [None, Decimal(3000)]
    assert [(record.getMessage(), record.__dict__["asset"]) for record in caplog.records] == [
        ("prezzo effettivo non disponibile", "BTC")
    ]
