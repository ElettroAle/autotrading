import pytest

from autotrading.domain.sources.errors import (
    InvalidSourceParameterError,
    SourceListValueOutOfRangeError,
    SourceParameterRefusedError,
    TooManySourceListValuesError,
)
from autotrading.domain.sources.source_list_parameter import MAXIMUM_VALUES, SourceListParameter


def trend_days(default: tuple[int, ...] = ()) -> SourceListParameter:
    return SourceListParameter("tendenza_giorni", "tendenza giorni", default=default, minimum=1, maximum=3650)


def test_a_list_is_saved_ordered_and_without_repetitions() -> None:
    assert trend_days().accepted([50, 20, 50]) == (20, 50)


def test_an_empty_list_is_accepted() -> None:
    assert trend_days().accepted([]) == ()


def test_a_tuple_is_accepted_as_a_list() -> None:
    assert trend_days().accepted((90, 3)) == (3, 90)


@pytest.mark.parametrize("value", [[0], [3651], [7, 0]])
def test_a_value_outside_the_range_is_refused_naming_the_range(value: list[int]) -> None:
    with pytest.raises(SourceListValueOutOfRangeError) as raised:
        trend_days().accepted(value)

    assert (str(raised.value), raised.value.status_code, raised.value.details) == (
        "tendenza giorni: ogni valore tra 1 e 3650",
        422,
        {"field": "tendenza_giorni", "minimum": 1, "maximum": 3650},
    )


@pytest.mark.parametrize("value", [7, "7", [True], [7.0], ["7"], None])
def test_a_value_that_is_not_a_list_of_whole_numbers_is_refused(value: object) -> None:
    with pytest.raises(SourceListValueOutOfRangeError):
        trend_days().accepted(value)


def test_more_values_than_declared_are_refused_naming_the_maximum() -> None:
    with pytest.raises(TooManySourceListValuesError) as raised:
        trend_days().accepted(list(range(1, MAXIMUM_VALUES + 2)))

    assert (str(raised.value), raised.value.details) == (
        "tendenza giorni: al massimo 8 valori",
        {"field": "tendenza_giorni", "maximum_values": 8},
    )


def test_repetitions_do_not_count_towards_the_maximum() -> None:
    assert trend_days().accepted([*range(1, MAXIMUM_VALUES + 1), 1]) == tuple(range(1, MAXIMUM_VALUES + 1))


def test_both_refusals_are_refusals_of_a_parameter() -> None:
    assert issubclass(SourceListValueOutOfRangeError, SourceParameterRefusedError)
    assert issubclass(TooManySourceListValuesError, SourceParameterRefusedError)


@pytest.mark.parametrize(
    ("default", "minimum", "maximum", "maximum_values"),
    [
        ((0,), 1, 3650, 8),
        ((20, 7), 1, 3650, 8),
        ((7, 7), 1, 3650, 8),
        ((1, 2, 3), 1, 3650, 2),
        ((), 10, 1, 8),
        ((), 1, 10, 0),
    ],
)
def test_a_declaration_that_breaks_its_own_rules_is_refused(
    default: tuple[int, ...], minimum: int, maximum: int, maximum_values: int
) -> None:
    with pytest.raises(InvalidSourceParameterError) as raised:
        SourceListParameter("medie_periodi", "medie periodi", default, minimum, maximum, maximum_values)

    assert raised.value.key == "medie_periodi"


def test_the_value_in_the_settings_is_the_one_the_flow_set() -> None:
    assert trend_days((7,)).value_in({"tendenza_giorni": (30, 90)}) == (30, 90)


def test_the_value_in_the_settings_is_the_default_when_the_flow_set_none() -> None:
    assert trend_days((7,)).value_in({"lunghezza_serie": 10}) == (7,)
