from autotrading.application.sources.list_sources import ListSourcesUseCase, SourceSystems
from autotrading.domain.sources.forecast import FORECAST
from autotrading.domain.sources.indicators import INDICATORS
from autotrading.domain.sources.news import NEWS
from autotrading.domain.sources.pivots import PIVOTS
from autotrading.domain.sources.sentiment import SENTIMENT
from autotrading.domain.sources.source_catalog import SOURCES
from tests.fakes.market_data import MARKET_DECLARATION, FakeMarketDataAdapter
from tests.fakes.price_forecaster import FORECASTER_DECLARATION, FakePriceForecasterAdapter
from tests.fakes.price_history import FakePriceHistoryAdapter
from tests.fakes.sources import FakeNewsAdapter, FakeSentimentAdapter

FIRST, SECOND = FakeSentimentAdapter("alternative.me"), FakeSentimentAdapter("CoinMarketCap")


def catalog_use_case() -> ListSourcesUseCase:
    systems = SourceSystems(
        (FIRST, SECOND),
        FakeNewsAdapter(),
        FakePriceHistoryAdapter(),
        FakePriceForecasterAdapter(),
        FakeMarketDataAdapter(),
    )
    return ListSourcesUseCase(systems)


def test_lists_every_source_of_the_platform_in_its_order() -> None:
    catalog = catalog_use_case().execute()

    assert tuple(source.definition for source in catalog.sources) == SOURCES


def test_every_source_has_the_adapters_that_declare_they_offer_it() -> None:
    catalog = catalog_use_case().execute()

    assert {source.name: source.adapters for source in catalog.sources} == {
        INDICATORS.name: (MARKET_DECLARATION,),
        PIVOTS.name: (MARKET_DECLARATION,),
        FORECAST.name: (FORECASTER_DECLARATION,),
        SENTIMENT.name: (FIRST.declaration(), SECOND.declaration()),
        NEWS.name: (FakeNewsAdapter().declaration(),),
    }
