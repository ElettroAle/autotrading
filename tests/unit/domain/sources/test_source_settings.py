import pytest

from autotrading.domain.sources.errors import (
    SourceParameterNotAmongChoicesError,
    SourceParameterOutOfRangeError,
    UnknownSourceParameterError,
)
from autotrading.domain.sources.source_definition import SourceDefinition
from autotrading.domain.sources.source_parameter import ParameterChoice, SourceParameter

NEWS = SourceDefinition(
    name="notizie",
    description="notizie recenti",
    per_asset=True,
    parameters=(
        SourceParameter(
            "max_items", "numero massimo di notizie", 10, 1, 50, description="Che cosa fa. Valori ammessi. Predefinito."
        ),
        SourceParameter("hours", "ore indietro", 24, 1, 72, description="Che cosa fa. Valori ammessi. Predefinito."),
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


def test_the_refusal_names_the_parameter_and_the_values_it_admits() -> None:
    with pytest.raises(SourceParameterOutOfRangeError) as raised:
        NEWS.settings({"max_items": 51})

    assert (str(raised.value), raised.value.label, raised.value.minimum, raised.value.maximum) == (
        "parametro fuori dai valori ammessi: numero massimo di notizie, da 1 a 50",
        "numero massimo di notizie",
        1,
        50,
    )


def test_the_refusal_tells_the_field_and_its_limits_to_the_page_of_a_trial() -> None:
    with pytest.raises(SourceParameterOutOfRangeError) as raised:
        NEWS.settings({"max_items": 0})

    assert (raised.value.status_code, raised.value.details) == (
        422,
        {"field": "max_items", "minimum": 1, "maximum": 50},
    )


def test_the_parameters_of_an_adapter_are_checked_with_those_of_the_source() -> None:
    own = SourceParameter("lingua", "lingua", 1, 1, 3, description="Che cosa fa. Valori ammessi. Predefinito.")

    assert NEWS.settings({"lingua": 2}, (own,)) == {"max_items": 10, "hours": 24, "lingua": 2}


def test_a_parameter_the_source_does_not_have_is_refused() -> None:
    with pytest.raises(UnknownSourceParameterError, match=r"^parametro sconosciuto della fonte notizie: lingua$"):
        NEWS.settings({"lingua": 1})


def test_a_value_outside_the_choices_of_a_parameter_is_refused_listing_them() -> None:
    horizon = SourceParameter.of_choices(
        "orizzonte",
        "orizzonte",
        default=0,
        choices=(ParameterChoice(0, "nessuno"), ParameterChoice(1440, "1 giorno")),
        description="Che cosa fa. Valori ammessi. Predefinito.",
    )

    with pytest.raises(SourceParameterNotAmongChoicesError, match=r"^orizzonte: ammessi nessuno, 1 giorno$"):
        NEWS.settings({"orizzonte": 60}, (horizon,))
