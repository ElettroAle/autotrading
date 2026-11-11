from autotrading.application.sources.list_sources import ListSourcesUseCase
from autotrading.domain.sources.news import NEWS
from autotrading.domain.sources.pivots import PIVOTS
from autotrading.domain.sources.source_catalog import SourceCatalog


def test_lists_every_source_of_the_catalog() -> None:
    assert ListSourcesUseCase(SourceCatalog([PIVOTS, NEWS])).execute() == [PIVOTS, NEWS]
