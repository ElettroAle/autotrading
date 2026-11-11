import pytest

from autotrading.domain.sources.errors import SourceNotAvailableError
from autotrading.domain.sources.source_catalog import SourceCatalog
from autotrading.domain.sources.source_definition import SourceDefinition


def definition(name: str) -> SourceDefinition:
    return SourceDefinition(name, f"fonte {name}", per_asset=True, parameters=())


def test_lists_the_sources_in_the_order_they_were_declared() -> None:
    catalog = SourceCatalog([definition("pivot"), definition("indicatori")])

    assert [source.name for source in catalog.sources] == ["pivot", "indicatori"]


def test_finds_a_source_by_name() -> None:
    assert SourceCatalog([definition("pivot")]).find("pivot") == definition("pivot")


def test_a_source_not_in_the_catalog_is_not_available() -> None:
    with pytest.raises(SourceNotAvailableError) as raised:
        SourceCatalog([definition("pivot")]).find("oroscopo")

    assert (str(raised.value), raised.value.name, raised.value.status_code) == (
        "fonte non disponibile: oroscopo",
        "oroscopo",
        404,
    )
