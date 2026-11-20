from dataclasses import dataclass

from autotrading.application.sources.ports import (
    MarketDataPort,
    NewsPort,
    PriceForecasterPort,
    PriceHistoryPort,
    SentimentPort,
    VolumesPort,
    WhaleTransfersPort,
)
from autotrading.domain.sources.forecast import FORECAST
from autotrading.domain.sources.indicators import INDICATORS
from autotrading.domain.sources.news import NEWS
from autotrading.domain.sources.pivots import PIVOTS
from autotrading.domain.sources.sentiment import SENTIMENT
from autotrading.domain.sources.source_catalog import OfferedSource, SourceCatalog
from autotrading.domain.sources.volumes import VOLUMES
from autotrading.domain.sources.whale import WHALE


@dataclass(frozen=True, slots=True)
class SourceSystems:
    """The systems the sources of the catalog read, the same for every tenant (ADR 0042): every adapter of a source
    declares itself (R4.1.1).
    """

    sentiments: tuple[SentimentPort, ...]
    news: NewsPort
    prices: PriceHistoryPort
    forecaster: PriceForecasterPort
    market: MarketDataPort
    whales: tuple[WhaleTransfersPort, ...]
    volumes: tuple[VolumesPort, ...]


class ListSourcesUseCase:
    """The sources a flow can activate, each with the adapters that offer it as they declare themselves (R1.3.1,
    R4.1.1, ADR fonti-con-adapter-dichiarati). A source no adapter offers is not activatable, so it is not listed.
    """

    def __init__(self, systems: SourceSystems) -> None:
        self._systems = systems

    def execute(self) -> SourceCatalog:
        systems = self._systems
        market = systems.market.declaration()
        offered = (
            OfferedSource(INDICATORS, (market,)),
            OfferedSource(PIVOTS, (market,)),
            OfferedSource(FORECAST, (systems.forecaster.declaration(),)),
            OfferedSource(SENTIMENT, tuple(sentiment.declaration() for sentiment in systems.sentiments)),
            OfferedSource(NEWS, (systems.news.declaration(),)),
            OfferedSource(WHALE, tuple(whales.declaration() for whales in systems.whales)),
            OfferedSource(VOLUMES, tuple(volumes.declaration() for volumes in systems.volumes)),
        )
        return SourceCatalog(source for source in offered if source.adapters)
