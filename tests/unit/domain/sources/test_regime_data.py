from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from autotrading.domain.sources.candle import Candle
from autotrading.domain.sources.errors import (
    SourceListValueOutOfRangeError,
    SourceParameterOutOfRangeError,
    TimeframeNotAvailableError,
)
from autotrading.domain.sources.indicators import INDICATORS
from autotrading.domain.sources.regime_data import (
    CHANGE_HOURS,
    CLOSE_SERIES,
    CLOSE_SERIES_NAME,
    EXTREMES_HOURS,
    HOURLY_TIMEFRAME,
    REGIME_PARAMETERS,
    RegimeChoice,
    hourly_timeframe_of,
)
from autotrading.domain.sources.source_list_parameter import SourceListParameter
from autotrading.domain.sources.source_parameter import SourceParameterValue
from autotrading.domain.sources.timeframe import Timeframe

# The close of the last hourly candle: the hour just ended.
LAST_CLOSE = datetime(2026, 11, 26, 10, tzinfo=UTC)
PRICE = Decimal("2.70")


def hourly(lows_and_highs: list[tuple[str, str]], closes: list[str] | None = None) -> list[Candle]:
    last = len(lows_and_highs) - 1
    every_close = closes or [low for low, _ in lows_and_highs]
    return [
        Candle(LAST_CLOSE - timedelta(hours=last - index), Decimal(close), Decimal(1), Decimal(high), Decimal(low))
        for index, ((low, high), close) in enumerate(zip(lows_and_highs, every_close, strict=True))
    ]


def flat(count: int, close: str = "2.60") -> list[Candle]:
    return hourly([(close, close)] * count)


def choice(extremes: tuple[int, ...] = (), changes: tuple[int, ...] = (), series: bool = False) -> RegimeChoice:
    return RegimeChoice(extremes, changes, series)


# The parameters


def test_the_hours_are_lists_and_the_series_a_switch_all_off_by_default() -> None:
    lists = [
        (p.key, p.label, p.default, p.minimum, p.maximum, p.maximum_values) for p in (EXTREMES_HOURS, CHANGE_HOURS)
    ]

    assert lists == [
        ("estremi_ore", "estremi_ore", (), 1, 720, 8),
        ("variazione_ore", "variazione_ore", (), 1, 720, 8),
    ]
    assert (CLOSE_SERIES.key, CLOSE_SERIES.default, CLOSE_SERIES.minimum, CLOSE_SERIES.maximum) == (
        "serie_chiusure",
        0,
        0,
        1,
    )
    assert REGIME_PARAMETERS == (EXTREMES_HOURS, CHANGE_HOURS, CLOSE_SERIES)


def test_the_parameters_are_not_of_the_source_but_of_its_adapter() -> None:
    assert not set(REGIME_PARAMETERS) & set(INDICATORS.parameters)


@pytest.mark.parametrize("parameter", [EXTREMES_HOURS, CHANGE_HOURS])
@pytest.mark.parametrize("value", [[0], [721]])
def test_hours_out_of_range_are_refused_in_the_words_of_the_requirement(
    parameter: SourceListParameter, value: list[int]
) -> None:
    with pytest.raises(SourceListValueOutOfRangeError, match=rf"^{parameter.key} va da 1 a 720$"):
        parameter.accepted(value)


def test_a_series_switch_other_than_zero_or_one_is_refused_in_the_words_of_the_requirement() -> None:
    with pytest.raises(SourceParameterOutOfRangeError, match=r"^serie_chiusure vale 0 oppure 1$"):
        CLOSE_SERIES.accepted(2)


def test_a_choice_follows_the_settings_and_the_defaults() -> None:
    settings: dict[str, SourceParameterValue] = {"estremi_ore": (24, 72), "variazione_ore": (4,), "serie_chiusure": 1}

    assert RegimeChoice.of(settings) == choice((24, 72), (4,), series=True)
    assert RegimeChoice.of({}) == choice()


# The hourly candles


@pytest.mark.parametrize(
    ("chosen", "reads"),
    [(choice(), False), (choice(series=True), False), (choice((24,)), True), (choice(changes=(4,)), True)],
)
def test_the_hourly_candles_are_read_only_for_extremes_or_changes(chosen: RegimeChoice, reads: bool) -> None:
    assert chosen.reads_hourly_candles is reads


@pytest.mark.parametrize(
    ("chosen", "candles"),
    [(choice((24, 72)), 72), (choice(changes=(4,)), 5), (choice((24,), (24,)), 25), (choice((72,), (4,)), 72)],
)
def test_the_hourly_candles_are_those_of_the_longest_value(chosen: RegimeChoice, candles: int) -> None:
    assert chosen.hourly_candles == candles


def test_the_hourly_timeframe_is_the_one_hour_candle_of_the_market() -> None:
    assert hourly_timeframe_of((Timeframe(15), Timeframe(60))) == HOURLY_TIMEFRAME == Timeframe(60)


def test_a_market_without_hourly_candles_has_no_regime_data() -> None:
    with pytest.raises(TimeframeNotAvailableError):
        hourly_timeframe_of((Timeframe(15), Timeframe(240)))


# The extremes


def test_the_extremes_are_the_lowest_low_and_the_highest_high_of_the_last_hours() -> None:
    candles = hourly([("2.00", "3.50"), ("2.80", "3.00"), ("2.50", "2.90"), ("2.60", "2.70")])

    values = choice((3,)).hourly_values(candles, PRICE).values

    assert values["estremi.minimo_3h"] == Decimal("2.50")
    assert values["estremi.massimo_3h"] == Decimal("3.00")


def test_the_distances_follow_the_formulas_of_the_requirement() -> None:
    candles = hourly([("2.50", "2.60"), ("2.60", "3.00")])

    values = choice((2,)).hourly_values(candles, PRICE).values

    assert values["estremi.dal_minimo_2h"] == Decimal(8)
    assert values["estremi.dal_massimo_2h"] == Decimal(-10)


def test_every_window_gives_its_four_values() -> None:
    values = choice((1, 3)).hourly_values(flat(5), PRICE).values

    assert set(values) == {
        f"estremi.{name}_{hours}h" for hours in (1, 3) for name in ("minimo", "massimo", "dal_minimo", "dal_massimo")
    }


def test_a_window_longer_than_the_history_is_missing_with_its_four_values() -> None:
    computed = choice((3, 720)).hourly_values(flat(100), PRICE)

    assert not [name for name in computed.values if name.endswith("_720h")]
    assert [(each.name, each.reason) for each in computed.missing] == [
        (f"estremi.{name}_720h", "storico di 100 candele orarie")
        for name in ("minimo", "massimo", "dal_minimo", "dal_massimo")
    ]
    assert "estremi.minimo_3h" in computed.values


# The changes over hours


def test_the_change_is_against_the_close_of_n_hours_ago() -> None:
    candles = hourly([("2.60", "2.60")] * 6, ["2.60", "2.40", "2.60", "2.60", "2.60", "2.60"])

    values = choice(changes=(4,)).hourly_values(candles, PRICE).values

    assert values == {"tendenza.variazione_4h": Decimal("12.5")}


def test_a_change_longer_than_the_history_is_missing() -> None:
    computed = choice(changes=(4, 5)).hourly_values(flat(5), PRICE)

    assert set(computed.values) == {"tendenza.variazione_4h"}
    assert [(each.name, each.reason) for each in computed.missing] == [
        ("tendenza.variazione_5h", "storico di 5 candele orarie")
    ]


def test_no_hours_give_no_values() -> None:
    computed = choice().hourly_values(flat(3), PRICE)

    assert (dict(computed.values), computed.missing) == ({}, ())


# The series of the closes


def test_the_series_of_the_closes_is_the_last_ones_oldest_first() -> None:
    candles = hourly([("1", "1")] * 4, ["1", "2", "3", "4"])

    assert choice(series=True).closes(candles, 3) == {CLOSE_SERIES_NAME: [Decimal(2), Decimal(3), Decimal(4)]}


def test_without_the_switch_there_is_no_series() -> None:
    assert choice().closes(flat(3), 2) == {}
