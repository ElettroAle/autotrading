from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from autotrading.application.sources.collect_cycle_source import CollectCycleSourceUseCase, SourceSystems
from autotrading.domain.sources.indicators import INDICATORS
from autotrading.domain.sources.sentiment import SENTIMENT_ALTERNATIVE_ME
from autotrading.domain.sources.source_catalog import SOURCE_CATALOG
from autotrading.domain.sources.source_sample import CycleReference
from tests.fakes.forecast_repository import InMemoryForecastRepositoryAdapter
from tests.fakes.market_data import FakeMarketDataAdapter
from tests.fakes.price_history import FakePriceHistoryAdapter
from tests.fakes.source_readers import InMemorySampleRepositoryAdapter
from tests.fakes.sources import FakeNewsAdapter, FakeSentimentAdapter

PLANNED_AT = datetime(2026, 11, 13, 10, 0, tzinfo=UTC)
ASKED_AT = datetime(2026, 11, 13, 10, 0, 2, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class Ask:
    source: str
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
        systems = SourceSystems(
            {SENTIMENT_ALTERNATIVE_ME.name: FakeSentimentAdapter(SENTIMENT_ALTERNATIVE_ME.name)},
            FakeNewsAdapter(),
            FakePriceHistoryAdapter(),
            self.market,
        )
        self.collect = CollectCycleSourceUseCase(
            SOURCE_CATALOG, systems, InMemoryForecastRepositoryAdapter(), self.samples
        )


def test_the_source_is_collected_with_the_weight_of_the_flow_and_recorded_for_the_cycle() -> None:
    world = World()
    ask = Ask(SENTIMENT_ALTERNATIVE_ME.name)

    collected = world.collect.execute(ask)

    assert (collected.source, collected.weight) == (SENTIMENT_ALTERNATIVE_ME.name, 7)
    assert world.samples.samples == list(collected.samples)
    assert {sample.cycle for sample in collected.samples} == {CycleReference(ask.flow_id, PLANNED_AT)}


def test_the_indicators_read_the_candles_of_the_cycle_interval_of_the_flow() -> None:
    hourly, quarterly = World(), World()

    hourly.collect.execute(Ask(INDICATORS.name, cycle_minutes=60))
    quarterly.collect.execute(Ask(INDICATORS.name, cycle_minutes=15))

    assert {label for _, label, _ in hourly.market.requests} != {label for _, label, _ in quarterly.market.requests}
