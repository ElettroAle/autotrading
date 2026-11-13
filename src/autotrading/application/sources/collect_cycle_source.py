from collections.abc import Mapping
from dataclasses import dataclass

from autotrading.application.sources.collect_source import CollectedSource, CollectSourceCommand, CollectSourceUseCase
from autotrading.application.sources.forecast_asset import ForecastAssetUseCase
from autotrading.application.sources.ports import (
    CycleSourceAskPort,
    ForecastRepositoryPort,
    MarketDataPort,
    NewsPort,
    PriceHistoryPort,
    SampleRepositoryPort,
    SentimentPort,
    SourceReaderPort,
)
from autotrading.application.sources.read_forecast import ReadForecastUseCase
from autotrading.application.sources.read_indicators import ReadIndicatorsUseCase
from autotrading.application.sources.read_news import ReadNewsUseCase
from autotrading.application.sources.read_pivots import ReadPivotsUseCase
from autotrading.application.sources.read_sentiment import ReadSentimentUseCase
from autotrading.domain.sources.forecast import FORECAST
from autotrading.domain.sources.indicators import INDICATORS
from autotrading.domain.sources.news import NEWS
from autotrading.domain.sources.pivots import PIVOTS
from autotrading.domain.sources.source_catalog import SourceCatalog
from autotrading.domain.sources.source_sample import CycleReference


@dataclass(frozen=True, slots=True)
class SourceSystems:
    """The systems the sources of the catalog read, the same for every tenant (ADR 0042)."""

    sentiments: Mapping[str, SentimentPort]
    news: NewsPort
    prices: PriceHistoryPort
    market: MarketDataPort


class CollectCycleSourceUseCase:
    """Collects an active source of a flow for one cycle and records it for the tenant (R1.3.2-R1.3.8, ADR 0042).

    The readers depend on the cycle: the indicators read candles of the cycle interval of the flow (R1.3.3).
    """

    def __init__(
        self,
        catalog: SourceCatalog,
        systems: SourceSystems,
        forecasts: ForecastRepositoryPort,
        samples: SampleRepositoryPort,
    ) -> None:
        self._catalog = catalog
        self._systems = systems
        self._forecasts = forecasts
        self._samples = samples

    def execute(self, ask: CycleSourceAskPort) -> CollectedSource:
        command = CollectSourceCommand(
            CycleReference(ask.flow_id, ask.planned_at),
            ask.source,
            ask.weight,
            ask.parameters,
            ask.assets,
            ask.asked_at,
        )
        return CollectSourceUseCase(self._catalog, self._readers_of(ask.cycle_minutes), self._samples).execute(command)

    def _readers_of(self, cycle_minutes: int) -> dict[str, SourceReaderPort]:
        systems = self._systems
        readers: dict[str, SourceReaderPort] = {
            name: ReadSentimentUseCase(sentiment) for name, sentiment in systems.sentiments.items()
        }
        readers[NEWS.name] = ReadNewsUseCase(systems.news)
        readers[FORECAST.name] = ReadForecastUseCase(ForecastAssetUseCase(systems.prices, self._forecasts))
        readers[INDICATORS.name] = ReadIndicatorsUseCase(systems.market, cycle_minutes)
        readers[PIVOTS.name] = ReadPivotsUseCase(systems.market)
        return readers
