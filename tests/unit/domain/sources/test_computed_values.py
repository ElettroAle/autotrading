from decimal import Decimal

from autotrading.domain.sources.computed_values import ComputedValues, MissingValue, short_history


def test_nothing_missing_has_no_note() -> None:
    assert ComputedValues({"EMA20": Decimal(1)}).missing_note() == {}


def test_the_missing_values_with_the_same_reason_are_named_together() -> None:
    computed = ComputedValues(
        missing=(
            MissingValue("EMA500", "storico di 300 candele"),
            MissingValue("tendenza.variazione_90g", "storico di 40 giorni chiusi"),
            MissingValue("MA500", "storico di 300 candele"),
        )
    )

    assert computed.missing_note() == {
        "dati_mancanti": "EMA500, MA500: storico di 300 candele; tendenza.variazione_90g: storico di 40 giorni chiusi"
    }


def test_a_prefix_names_the_values_and_the_missing_ones() -> None:
    computed = ComputedValues({"EMA20": Decimal(1)}, (MissingValue("EMA500", "storico di 3 candele"),))

    prefixed = computed.prefixed("breve.")

    assert prefixed == ComputedValues(
        {"breve.EMA20": Decimal(1)}, (MissingValue("breve.EMA500", "storico di 3 candele"),)
    )


def test_two_computations_join_values_and_missing_ones() -> None:
    first = ComputedValues({"a": Decimal(1)}, (MissingValue("b", "x"),))
    second = ComputedValues({"c": "testo"}, (MissingValue("d", "y"),))

    assert first | second == ComputedValues(
        {"a": Decimal(1), "c": "testo"}, (MissingValue("b", "x"), MissingValue("d", "y"))
    )


def test_the_reason_of_a_short_history_names_what_there_is() -> None:
    assert short_history(40, "giorni chiusi") == "storico di 40 giorni chiusi"
