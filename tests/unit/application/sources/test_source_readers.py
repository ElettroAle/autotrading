from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from autotrading.application.sources.ports import SourceRequest
from autotrading.application.sources.source_readers import readers_of
from tests.fakes.forecast_repository import InMemoryForecastRepositoryAdapter
from tests.fakes.market_data import FakeMarketDataAdapter
from tests.fakes.whale_transfers import FakeWhaleTransfersAdapter
from tests.support.source_selections import platform_systems

NOW = datetime(2026, 11, 19, 10, 0, tzinfo=UTC)


def test_every_adapter_of_every_source_has_its_reader_by_the_name_it_declares() -> None:
    readers = readers_of(platform_systems(), InMemoryForecastRepositoryAdapter(), 15)

    assert sorted(readers) == [
        ("forecast", "Prophet"),
        ("indicatori", "Hyperliquid"),
        ("notizie", "RSS"),
        ("pivot", "Hyperliquid"),
        ("sentiment", "CoinMarketCap"),
        ("sentiment", "alternative.me"),
    ]


def test_the_indicators_read_the_candles_of_the_interval_given() -> None:
    systems = platform_systems()
    market = systems.market
    assert isinstance(market, FakeMarketDataAdapter)

    readers_of(systems, InMemoryForecastRepositoryAdapter(), 60)["indicatori", "Hyperliquid"].execute(
        SourceRequest(uuid4(), "BTC", {"lunghezza_serie": 5}, NOW)
    )

    assert [label for _, label, _ in market.requests] == ["1h", "4h"]


def test_the_forecast_is_recorded_for_the_flow_that_reads_it() -> None:
    forecasts = InMemoryForecastRepositoryAdapter()
    flow_id = uuid4()

    readers_of(platform_systems(), forecasts, 15)["forecast", "Prophet"].execute(
        SourceRequest(flow_id, "BTC", {"profondita_storico_giorni": 7}, NOW)
    )

    assert {forecast.flow_id for forecast in forecasts.forecasts} == {flow_id}


def test_every_provider_of_the_large_transfers_reads_the_last_cycle_interval() -> None:
    whales = FakeWhaleTransfersAdapter("Balene")
    systems = replace(platform_systems(), whales=(whales,))

    readers_of(systems, InMemoryForecastRepositoryAdapter(), 30)["whale", "Balene"].execute(
        SourceRequest(uuid4(), None, {"soglia_usd": 1_000_000}, NOW)
    )

    assert [(asked.since, asked.until) for asked in whales.asked] == [(NOW - timedelta(minutes=30), NOW)]
