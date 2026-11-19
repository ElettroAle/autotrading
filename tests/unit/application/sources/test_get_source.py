import pytest

from autotrading.application.sources.get_source import GetSourceCommand, GetSourceUseCase
from autotrading.application.sources.list_sources import ListSourcesUseCase, SourceSystems
from autotrading.domain.sources.errors import SourceNotAvailableError
from autotrading.domain.sources.news import NEWS
from tests.fakes.market_data import FakeMarketDataAdapter
from tests.fakes.price_forecaster import FakePriceForecasterAdapter
from tests.fakes.price_history import FakePriceHistoryAdapter
from tests.fakes.sources import FakeNewsAdapter, FakeSentimentAdapter

SOURCES = ListSourcesUseCase(
    SourceSystems(
        (FakeSentimentAdapter("alternative.me"),),
        FakeNewsAdapter(),
        FakePriceHistoryAdapter(),
        FakePriceForecasterAdapter(),
        FakeMarketDataAdapter(),
    )
)


def test_reads_one_source_of_the_catalog_with_its_adapters() -> None:
    source = GetSourceUseCase(SOURCES).execute(GetSourceCommand("notizie"))

    assert (source.definition, [adapter.name for adapter in source.adapters]) == (NEWS, ["RSS"])


def test_a_source_outside_the_catalog_is_not_available() -> None:
    with pytest.raises(SourceNotAvailableError):
        GetSourceUseCase(SOURCES).execute(GetSourceCommand("oroscopo"))
