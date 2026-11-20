from autotrading.application.sources.collect_source import Reader
from autotrading.application.sources.forecast_asset import ForecastAssetUseCase
from autotrading.application.sources.list_sources import SourceSystems
from autotrading.application.sources.ports import ForecastRepositoryPort, SourceReaderPort
from autotrading.application.sources.read_forecast import ReadForecastUseCase
from autotrading.application.sources.read_indicators import ReadIndicatorsUseCase
from autotrading.application.sources.read_news import ReadNewsUseCase
from autotrading.application.sources.read_pivots import ReadPivotsUseCase
from autotrading.application.sources.read_sentiment import ReadSentimentUseCase
from autotrading.application.sources.read_social import ReadSocialUseCase
from autotrading.application.sources.read_volumes import ReadVolumesUseCase
from autotrading.application.sources.read_whale_transfers import ReadWhaleTransfersUseCase
from autotrading.domain.sources.forecast import FORECAST
from autotrading.domain.sources.indicators import INDICATORS
from autotrading.domain.sources.news import NEWS
from autotrading.domain.sources.pivots import PIVOTS
from autotrading.domain.sources.sentiment import SENTIMENT
from autotrading.domain.sources.social import SOCIAL
from autotrading.domain.sources.volumes import VOLUMES
from autotrading.domain.sources.whale import WHALE


def readers_of(
    systems: SourceSystems, forecasts: ForecastRepositoryPort, cycle_minutes: int
) -> dict[Reader, SourceReaderPort]:
    """The reader of every adapter of every source, by the source and the name the adapter declares: the same for the
    cycles and for the trials (R4.1.1, R6.3.1, ADR prova-di-un-adapter-di-fonte-nel-worker).

    The indicators read candles of the cycle interval, the large transfers and the aggressive trades of the volumes its
    last interval (R1.3.3, R5.1.1, R5.1.2); the forecasts are recorded only for a flow (R1.3.5).
    """
    market = systems.market.declaration().name
    readers: dict[Reader, SourceReaderPort] = {
        (SENTIMENT.name, sentiment.declaration().name): ReadSentimentUseCase(sentiment)
        for sentiment in systems.sentiments
    }
    readers[NEWS.name, systems.news.declaration().name] = ReadNewsUseCase(systems.news)
    readers[FORECAST.name, systems.forecaster.declaration().name] = ReadForecastUseCase(
        ForecastAssetUseCase(systems.prices, systems.forecaster, forecasts)
    )
    readers[INDICATORS.name, market] = ReadIndicatorsUseCase(systems.market, cycle_minutes)
    readers[PIVOTS.name, market] = ReadPivotsUseCase(systems.market)
    for whales in systems.whales:
        readers[WHALE.name, whales.declaration().name] = ReadWhaleTransfersUseCase(whales, cycle_minutes)
    for volumes in systems.volumes:
        readers[VOLUMES.name, volumes.declaration().name] = ReadVolumesUseCase(volumes, cycle_minutes)
    for social in systems.socials:
        readers[SOCIAL.name, social.declaration().name] = ReadSocialUseCase(social)
    return readers
