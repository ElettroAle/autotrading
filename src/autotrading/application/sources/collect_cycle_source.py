from autotrading.application.sources.collect_source import (
    CollectedSource,
    CollectSourceCommand,
    CollectSourceUseCase,
    Reader,
)
from autotrading.application.sources.forecast_asset import ForecastAssetUseCase
from autotrading.application.sources.list_sources import ListSourcesUseCase, SourceSystems
from autotrading.application.sources.ports import (
    CycleSourceAskPort,
    ForecastRepositoryPort,
    SampleRepositoryPort,
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
from autotrading.domain.sources.sentiment import SENTIMENT
from autotrading.domain.sources.source_sample import CycleReference


class CollectCycleSourceUseCase:
    """Collects an adapter of an active source of a flow for one cycle and records it for the tenant (R1.3.2-R1.3.8,
    R4.1.1, ADR 0042).

    The readers depend on the cycle: the indicators read candles of the cycle interval of the flow (R1.3.3). Every
    reader is registered by its source and by the name the adapter declares.
    """

    def __init__(
        self,
        systems: SourceSystems,
        forecasts: ForecastRepositoryPort,
        samples: SampleRepositoryPort,
    ) -> None:
        self._systems = systems
        self._forecasts = forecasts
        self._samples = samples

    def execute(self, ask: CycleSourceAskPort) -> CollectedSource:
        command = CollectSourceCommand(
            CycleReference(ask.flow_id, ask.planned_at),
            ask.source,
            ask.adapter,
            ask.weight,
            ask.parameters,
            ask.assets,
            ask.asked_at,
        )
        catalog = ListSourcesUseCase(self._systems).execute()
        return CollectSourceUseCase(catalog, self._readers_of(ask.cycle_minutes), self._samples).execute(command)

    def _readers_of(self, cycle_minutes: int) -> dict[Reader, SourceReaderPort]:
        systems = self._systems
        market = systems.market.declaration().name
        readers: dict[Reader, SourceReaderPort] = {
            (SENTIMENT.name, sentiment.declaration().name): ReadSentimentUseCase(sentiment)
            for sentiment in systems.sentiments
        }
        readers[NEWS.name, systems.news.declaration().name] = ReadNewsUseCase(systems.news)
        readers[FORECAST.name, systems.forecaster.declaration().name] = ReadForecastUseCase(
            ForecastAssetUseCase(systems.prices, systems.forecaster, self._forecasts)
        )
        readers[INDICATORS.name, market] = ReadIndicatorsUseCase(systems.market, cycle_minutes)
        readers[PIVOTS.name, market] = ReadPivotsUseCase(systems.market)
        return readers
