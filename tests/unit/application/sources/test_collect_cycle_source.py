from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from autotrading.application.sources.collect_cycle_source import CollectCycleSourceUseCase
from autotrading.application.sources.list_sources import SourceSystems
from autotrading.domain.sources.errors import SourceAdapterNotAvailableError
from autotrading.domain.sources.forecast import FORECAST
from autotrading.domain.sources.indicators import INDICATORS
from autotrading.domain.sources.news import NEWS
from autotrading.domain.sources.pivots import PIVOTS
from autotrading.domain.sources.sentiment import SENTIMENT
from autotrading.domain.sources.sentiment_index import SentimentIndex
from autotrading.domain.sources.source_sample import CycleReference
from tests.fakes.forecast_repository import InMemoryForecastRepositoryAdapter
from tests.fakes.market_data import FakeMarketDataAdapter
from tests.fakes.price_forecaster import FakePriceForecasterAdapter
from tests.fakes.price_history import FakePriceHistoryAdapter
from tests.fakes.source_readers import InMemorySampleRepositoryAdapter
from tests.fakes.sources import UPDATED_AT, FakeNewsAdapter, FakeSentimentAdapter

PLANNED_AT = datetime(2026, 11, 13, 10, 0, tzinfo=UTC)
ASKED_AT = datetime(2026, 11, 13, 10, 0, 2, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class Ask:
    source: str
    adapter: str
    cycle_minutes: int = 15
    flow_id: UUID = field(default_factory=uuid4)
    planned_at: datetime = PLANNED_AT
    weight: int = 7
    parameters: dict[str, int] = field(default_factory=dict)
    assets: tuple[str, ...] = ("BTC",)
    asked_at: datetime = ASKED_AT


class World:
    def __init__(self) -> None:
        self.market = FakeMarketDataAdapter()
        self.samples = InMemorySampleRepositoryAdapter()
        self.alternative_me = FakeSentimentAdapter("alternative.me", SentimentIndex(72, "Greed", UPDATED_AT))
        self.coinmarketcap = FakeSentimentAdapter("CoinMarketCap", SentimentIndex(55, "Neutral", UPDATED_AT))
        systems = SourceSystems(
            (self.alternative_me, self.coinmarketcap),
            FakeNewsAdapter(),
            FakePriceHistoryAdapter(),
            FakePriceForecasterAdapter(),
            self.market,
        )
        self.collect = CollectCycleSourceUseCase(systems, InMemoryForecastRepositoryAdapter(), self.samples)


def test_the_source_is_collected_with_its_adapter_and_the_weight_of_the_flow_and_recorded_for_the_cycle() -> None:
    world = World()
    ask = Ask(SENTIMENT.name, "alternative.me")

    collected = world.collect.execute(ask)

    assert (collected.source, collected.adapter, collected.weight) == (SENTIMENT.name, "alternative.me", 7)
    assert world.samples.samples == list(collected.samples)
    assert {sample.cycle for sample in collected.samples} == {CycleReference(ask.flow_id, PLANNED_AT)}


def test_each_adapter_of_the_sentiment_reads_its_own_provider() -> None:
    world = World()

    first = world.collect.execute(Ask(SENTIMENT.name, "alternative.me"))
    second = world.collect.execute(Ask(SENTIMENT.name, "CoinMarketCap"))

    assert [sample.values["valore"] for sample in (*first.samples, *second.samples)] == ["72", "55"]


@pytest.mark.parametrize(
    ("source", "adapter"),
    [(INDICATORS.name, "Hyperliquid"), (PIVOTS.name, "Hyperliquid"), (FORECAST.name, "Prophet"), (NEWS.name, "RSS")],
)
def test_every_source_is_read_by_the_adapter_it_declares(source: str, adapter: str) -> None:
    collected = World().collect.execute(Ask(source, adapter))

    assert (collected.source, collected.adapter) == (source, adapter)


def test_an_adapter_the_platform_does_not_offer_is_not_available() -> None:
    with pytest.raises(SourceAdapterNotAvailableError):
        World().collect.execute(Ask(SENTIMENT.name, "altro"))


def test_the_indicators_read_the_candles_of_the_cycle_interval_of_the_flow() -> None:
    hourly, quarterly = World(), World()

    hourly.collect.execute(Ask(INDICATORS.name, "Hyperliquid", cycle_minutes=60))
    quarterly.collect.execute(Ask(INDICATORS.name, "Hyperliquid", cycle_minutes=15))

    assert {label for _, label, _ in hourly.market.requests} != {label for _, label, _ in quarterly.market.requests}
