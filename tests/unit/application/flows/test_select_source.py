"""A source of the flow checked by the catalog of the platform (R1.3.1, ADR 0031)."""

import pytest

from autotrading.application.flows.errors import InvalidFlowSettingError
from autotrading.application.flows.select_source import SelectSourceUseCase
from autotrading.domain.flows.selections import SourceSelection
from autotrading.domain.sources.source_catalog import SOURCE_CATALOG


def test_a_source_gets_its_weight_and_its_parameters_with_the_defaults() -> None:
    sources = SelectSourceUseCase(SOURCE_CATALOG)
    news = SOURCE_CATALOG.find("notizie")
    first = news.parameters[0]

    assert sources.execute("notizie", None, {}) == SourceSelection("notizie", 5, news.settings({}))
    assert sources.execute("notizie", 8, {first.key: first.minimum}).parameters[first.key] == first.minimum


@pytest.mark.parametrize(
    ("source", "requested", "reason"),
    [
        ("oroscopo", {}, "fonte non disponibile: oroscopo"),
        ("notizie", {"lingua": 1}, "parametro sconosciuto della fonte notizie: lingua"),
    ],
)
def test_a_source_or_parameter_the_catalog_refuses_reaches_the_flow_with_the_reason(
    source: str, requested: dict[str, int], reason: str
) -> None:
    with pytest.raises(InvalidFlowSettingError) as raised:
        SelectSourceUseCase(SOURCE_CATALOG).execute(source, None, requested)

    assert str(raised.value) == reason


def test_a_source_parameter_out_of_range_reaches_the_flow_with_its_label() -> None:
    first = SOURCE_CATALOG.find("notizie").parameters[0]

    with pytest.raises(InvalidFlowSettingError, match=r"^parametro fuori dai valori ammessi: "):
        SelectSourceUseCase(SOURCE_CATALOG).execute("notizie", None, {first.key: first.maximum + 1})
