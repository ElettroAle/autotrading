import pytest

from autotrading.domain.sources.errors import (
    InvalidSourceParameterError,
    SourceParameterNotAmongChoicesError,
    SourceParameterOutOfRangeError,
    SourceParameterRefusedError,
)
from autotrading.domain.sources.source_parameter import ParameterChoice, SourceParameter, number_of


def news_count() -> SourceParameter:
    return SourceParameter("numero_notizie", "numero notizie", default=10, minimum=1, maximum=50)


@pytest.mark.parametrize("value", [1, 10, 50])
def test_accepts_the_values_within_its_range(value: int) -> None:
    assert news_count().accepts(value)


@pytest.mark.parametrize("value", [0, 51])
def test_refuses_the_values_outside_its_range(value: int) -> None:
    assert not news_count().accepts(value)


@pytest.mark.parametrize(("default", "minimum", "maximum"), [(0, 1, 50), (51, 1, 50), (5, 10, 1)])
def test_a_default_outside_the_range_or_an_empty_range_is_refused(default: int, minimum: int, maximum: int) -> None:
    with pytest.raises(InvalidSourceParameterError) as raised:
        SourceParameter("numero_notizie", "numero notizie", default=default, minimum=minimum, maximum=maximum)

    assert raised.value.key == "numero_notizie"


def long_horizon() -> SourceParameter:
    return SourceParameter.of_choices(
        "orizzonte_lungo",
        "orizzonte lungo",
        default=0,
        choices=(
            ParameterChoice(0, "nessuno"),
            ParameterChoice(1440, "1 giorno"),
            ParameterChoice(10080, "1 settimana"),
        ),
    )


@pytest.mark.parametrize("value", [0, 1440, 10080])
def test_a_parameter_with_choices_accepts_only_its_values(value: int) -> None:
    assert long_horizon().accepts(value)


@pytest.mark.parametrize("value", [1, 60, 2880])
def test_a_parameter_with_choices_refuses_the_values_between_them(value: int) -> None:
    assert not long_horizon().accepts(value)


def test_a_parameter_with_choices_spans_from_its_lowest_to_its_highest_value() -> None:
    parameter = long_horizon()

    assert (parameter.minimum, parameter.maximum, parameter.choice_labels) == (
        0,
        10080,
        ("nessuno", "1 giorno", "1 settimana"),
    )


def test_a_parameter_without_choices_names_none() -> None:
    assert (news_count().choices, news_count().choice_labels) == ((), ())


def test_a_default_outside_the_choices_is_refused() -> None:
    with pytest.raises(InvalidSourceParameterError) as raised:
        SourceParameter.of_choices(
            "orizzonte_lungo",
            "orizzonte lungo",
            default=60,
            choices=(ParameterChoice(0, "nessuno"), ParameterChoice(1440, "1 giorno")),
        )

    assert raised.value.key == "orizzonte_lungo"


def test_a_parameter_without_choices_to_offer_is_refused() -> None:
    with pytest.raises(InvalidSourceParameterError):
        SourceParameter.of_choices("orizzonte_lungo", "orizzonte lungo", default=0, choices=())


def test_a_value_outside_the_choices_is_refused_listing_their_labels() -> None:
    with pytest.raises(SourceParameterNotAmongChoicesError) as raised:
        long_horizon().accepted(129600)

    assert (str(raised.value), raised.value.status_code, raised.value.details) == (
        "orizzonte lungo: ammessi nessuno, 1 giorno, 1 settimana",
        422,
        {"field": "orizzonte_lungo", "choices": ["nessuno", "1 giorno", "1 settimana"]},
    )


def test_a_value_outside_the_range_is_refused_naming_the_range() -> None:
    with pytest.raises(
        SourceParameterOutOfRangeError, match=r"^parametro fuori dai valori ammessi: numero notizie, da 1 a 50$"
    ):
        news_count().accepted(51)


@pytest.mark.parametrize("value", [True, "1440", 1440.0])
def test_a_value_that_is_not_a_whole_number_is_refused_even_among_the_choices(value: object) -> None:
    with pytest.raises(SourceParameterNotAmongChoicesError):
        long_horizon().accepted(value)


def test_both_refusals_are_refusals_of_a_parameter() -> None:
    assert issubclass(SourceParameterNotAmongChoicesError, SourceParameterRefusedError)
    assert issubclass(SourceParameterOutOfRangeError, SourceParameterRefusedError)


def test_an_accepted_value_is_returned_as_it_is() -> None:
    assert (long_horizon().accepted(1440), news_count().accepted(10)) == (1440, 10)


def test_the_number_in_the_settings_is_the_one_the_flow_set() -> None:
    assert news_count().value_in({"numero_notizie": 5}) == 5


def test_the_number_in_the_settings_is_the_default_when_the_flow_set_none() -> None:
    assert news_count().value_in({}) == 10


def test_a_list_where_a_number_is_due_is_refused() -> None:
    with pytest.raises(SourceParameterOutOfRangeError):
        news_count().value_in({"numero_notizie": (5,)})


def test_a_whole_number_setting_is_read_as_it_is() -> None:
    assert number_of({"numero_notizie": 12}, "numero_notizie") == 12


def test_a_list_where_a_whole_number_is_expected_is_a_defect_of_the_source() -> None:
    with pytest.raises(InvalidSourceParameterError):
        number_of({"numero_notizie": (12,)}, "numero_notizie")


@pytest.mark.parametrize("value", [-1, 2])
def test_a_parameter_that_declares_its_refusal_is_refused_with_it(value: int) -> None:
    flag = SourceParameter("serie_chiusure", "serie_chiusure", 0, 0, 1, range_reason="serie_chiusure vale 0 oppure 1")

    with pytest.raises(SourceParameterOutOfRangeError) as raised:
        flag.accepted(value)

    assert (str(raised.value), raised.value.details) == (
        "serie_chiusure vale 0 oppure 1",
        {"field": "serie_chiusure", "minimum": 0, "maximum": 1},
    )
