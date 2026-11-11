import pytest

from autotrading.application.sources.get_source import GetSourceCommand, GetSourceUseCase
from autotrading.domain.sources.errors import SourceNotAvailableError
from autotrading.domain.sources.news import NEWS
from autotrading.domain.sources.source_catalog import SourceCatalog


def test_reads_one_source_of_the_catalog() -> None:
    assert GetSourceUseCase(SourceCatalog([NEWS])).execute(GetSourceCommand("notizie")) == NEWS


def test_a_source_outside_the_catalog_is_not_available() -> None:
    with pytest.raises(SourceNotAvailableError):
        GetSourceUseCase(SourceCatalog([NEWS])).execute(GetSourceCommand("oroscopo"))
