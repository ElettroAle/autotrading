import pytest

from autotrading.domain.sources.errors import SourceParameterOutOfRangeError, UnknownSourceParameterError
from autotrading.domain.sources.source_definition import SourceDefinition
from autotrading.domain.sources.source_parameter import SourceParameter

NEWS = SourceDefinition(
    name="notizie",
    description="notizie recenti",
    per_asset=True,
    parameters=(
        SourceParameter("max_items", "numero massimo di notizie", 10, 1, 50),
        SourceParameter("hours", "ore indietro", 24, 1, 72),
    ),
)


def test_a_flow_gets_the_defaults_of_the_parameters_it_does_not_set() -> None:
    assert NEWS.settings({"hours": 6}) == {"max_items": 10, "hours": 6}


@pytest.mark.parametrize("value", [1, 50])
def test_a_value_within_the_range_is_kept(value: int) -> None:
    assert NEWS.settings({"max_items": value})["max_items"] == value


@pytest.mark.parametrize("value", [0, 51, True, "5"])
def test_a_value_outside_the_range_or_not_whole_is_refused(value: object) -> None:
    with pytest.raises(SourceParameterOutOfRangeError, match=r"^parametro fuori dai valori ammessi: numero massimo"):
        NEWS.settings({"max_items": value})  # type: ignore[dict-item]  # what an untyped request could carry


def test_a_parameter_the_source_does_not_have_is_refused() -> None:
    with pytest.raises(UnknownSourceParameterError, match=r"^parametro sconosciuto della fonte notizie: lingua$"):
        NEWS.settings({"lingua": 1})
