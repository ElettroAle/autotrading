import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from autotrading.domain.sources.candle import Candle
from autotrading.domain.sources.errors import InsufficientHistoryError
from autotrading.domain.sources.extended_indicators import (
    EXTENDED_PARAMETERS,
    DominantCycle,
    ExtendedIndicatorChoice,
    GannAngles,
    dominant_cycle,
    fibonacci_levels,
    gann_angles,
)

START = datetime(2026, 11, 19, tzinfo=UTC)


def candle(index: int, close: Decimal, high: Decimal | None = None, low: Decimal | None = None) -> Candle:
    return Candle(
        START + timedelta(hours=4 * index),
        close,
        Decimal(1),
        close + 1 if high is None else high,
        close - 1 if low is None else low,
    )


def candles_of(closes: list[Decimal]) -> list[Candle]:
    return [candle(index, close) for index, close in enumerate(closes)]


def wave(count: int, period: int, phase_degrees: float = 0, trend: float = 0) -> list[Decimal]:
    """A cosine of the period given, at its peak where the phase is 0, on a straight line."""
    return [
        Decimal(
            str(
                round(100 + trend * index + 5 * math.cos(2 * math.pi * index / period + math.radians(phase_degrees)), 6)
            )
        )
        for index in range(count)
    ]


# The parameters


def test_the_windows_of_the_extended_indicators_are_lists_off_by_default() -> None:
    assert [(p.key, p.label, p.default, p.minimum, p.maximum, p.maximum_values) for p in EXTENDED_PARAMETERS] == [
        ("fibonacci_candele", "fibonacci candele", (), 10, 10000, 8),
        ("gann_candele", "gann candele", (), 10, 10000, 8),
        ("ciclo_candele", "ciclo candele", (), 10, 10000, 8),
    ]


def test_a_choice_reads_the_settings_and_the_defaults_for_what_they_do_not_say() -> None:
    assert ExtendedIndicatorChoice.of({"gann_candele": (50, 100)}) == ExtendedIndicatorChoice((), (50, 100), ())
    assert ExtendedIndicatorChoice.of({}) == ExtendedIndicatorChoice((), (), ())


@pytest.mark.parametrize(
    ("choice", "asked", "needed"),
    [
        (ExtendedIndicatorChoice((100, 300), (), ()), 110, 300),
        (ExtendedIndicatorChoice((), (), (50,)), 110, 110),
        (ExtendedIndicatorChoice((), (), ()), 110, 110),
    ],
)
def test_the_long_timeframe_reads_the_most_candles_between_those_asked_and_the_longest_window(
    choice: ExtendedIndicatorChoice, asked: int, needed: int
) -> None:
    assert choice.long_candles(asked) == needed


def test_the_fibonacci_levels_retrace_from_the_high_to_the_low() -> None:
    candles = [candle(0, Decimal(55000), low=Decimal(50000)), candle(1, Decimal(55000), high=Decimal(60000))]

    assert fibonacci_levels(candles) == {
        "minimo": Decimal(50000),
        "massimo": Decimal(60000),
        "23.6%": Decimal(57640),
        "38.2%": Decimal(56180),
        "50%": Decimal(55000),
        "61.8%": Decimal(53820),
        "78.6%": Decimal(52140),
    }


def test_the_fibonacci_levels_need_a_candle() -> None:
    with pytest.raises(InsufficientHistoryError):
        fibonacci_levels([])


# Gann


def test_the_gann_angles_climb_from_a_low_more_recent_than_the_high() -> None:
    candles = [
        candle(0, Decimal(100), high=Decimal(110), low=Decimal(100)),
        candle(1, Decimal(95), high=Decimal(100), low=Decimal(90)),
        candle(2, Decimal(100), high=Decimal(105), low=Decimal(95)),
        candle(3, Decimal(102), high=Decimal(105), low=Decimal(95)),
    ]

    # True ranges 10, 10 (high 100 - low 90), 10, 10: one unit of 10 per candle, two candles after the low.
    assert gann_angles(candles) == GannAngles(
        "minimo",
        Decimal(90),
        Decimal(10),
        {"1x1": Decimal(110), "1x2": Decimal(100), "2x1": Decimal(130)},
    )


def test_the_gann_angles_descend_from_a_high_more_recent_than_the_low() -> None:
    candles = [
        candle(0, Decimal(100), high=Decimal(101), low=Decimal(80)),
        candle(1, Decimal(110), high=Decimal(120), low=Decimal(100)),
        candle(2, Decimal(108), high=Decimal(110), low=Decimal(100)),
    ]

    # True ranges 21, 20 (high 120 - previous close 100), 10: unit 17, one candle after the high.
    angles = gann_angles(candles)

    assert (angles.pivot_side, angles.pivot, angles.unit) == ("massimo", Decimal(120), Decimal(17))
    assert angles.lines == {"1x1": Decimal(103), "1x2": Decimal("111.5"), "2x1": Decimal(86)}


def test_the_true_range_reaches_the_previous_close_when_the_candle_opens_with_a_gap() -> None:
    candles = [candle(0, Decimal(100), high=Decimal(100), low=Decimal(100)), candle(1, Decimal(80), Decimal(85))]

    # The second candle spans 85 to 79, but from the previous close 100 down to 79 the market moved 21.
    assert gann_angles(candles).unit == Decimal("10.5")


def test_a_candle_that_holds_both_extremes_starts_the_angles_from_its_low() -> None:
    candles = [candle(0, Decimal(100), high=Decimal(120), low=Decimal(80)), candle(1, Decimal(100))]

    assert gann_angles(candles).pivot_side == "minimo"


def test_the_gann_angles_need_a_candle() -> None:
    with pytest.raises(InsufficientHistoryError):
        gann_angles([])


# Dominant cycle


@pytest.mark.parametrize("period", [9, 16, 25])
def test_the_dominant_cycle_is_the_period_of_the_strongest_wave(period: int) -> None:
    assert dominant_cycle(candles_of(wave(100, period))).period == period


def test_the_trend_does_not_hide_the_cycle() -> None:
    assert dominant_cycle(candles_of(wave(100, 12, trend=3))).period == 12


@pytest.mark.parametrize(("start", "expected"), [(0, 0), (90, 90), (180, 180), (270, 270)])
def test_the_phase_is_the_angle_of_the_cycle_at_the_last_candle(start: float, expected: float) -> None:
    # The last of 97 candles comes after eight whole periods of 12: it is back at the angle of the first.
    cycle = dominant_cycle(candles_of(wave(97, 12, start)))

    distance = (cycle.phase - Decimal(expected)) % 360
    assert cycle.period == 12
    assert min(distance, 360 - distance) < 1


def test_the_phase_stays_below_a_full_turn() -> None:
    cycle = dominant_cycle(candles_of(wave(97, 12, -0.001)))

    assert Decimal(0) <= cycle.phase < Decimal(360)


def test_the_periods_go_from_4_candles_to_half_the_history() -> None:
    # A wave of 30 candles over 40: half the history is 20, so the longest period left is 20.
    assert dominant_cycle(candles_of(wave(40, 30))).period <= 20


def test_the_dominant_cycle_needs_two_periods_of_the_shortest_cycle() -> None:
    with pytest.raises(InsufficientHistoryError) as raised:
        dominant_cycle(candles_of(wave(7, 4)))

    assert (raised.value.needed, raised.value.available) == (8, 7)


# The values of a choice


def test_no_window_gives_no_value() -> None:
    computed = ExtendedIndicatorChoice((), (), ()).values(candles_of(wave(100, 9)))

    assert (computed.values, computed.missing) == ({}, ())


def test_every_window_gives_its_values_on_its_last_candles_named_after_it() -> None:
    candles = candles_of([Decimal(1000)] * 20 + wave(100, 9))
    choice = ExtendedIndicatorChoice((50, 100), (100,), (100,))

    values = choice.values(candles).values

    window = candles[-100:]
    assert "nota_storico" not in values
    assert values["fibonacci100.massimo"] == max(each.high for each in window)
    assert values["fibonacci100.50%"] == fibonacci_levels(window)["50%"]
    assert values["fibonacci50.50%"] == fibonacci_levels(candles[-50:])["50%"]
    angles = gann_angles(window)
    assert values["gann100.perno"] == angles.pivot_side
    assert values["gann100.prezzo_perno"] == angles.pivot
    assert values["gann100.unita_per_candela"] == angles.unit
    assert values["gann100.1x2"] == angles.lines["1x2"]
    assert values["ciclo100.periodo_candele"] == Decimal(9)
    assert values["ciclo100.fase_gradi"] == dominant_cycle(window).phase


def test_only_the_chosen_indicators_give_values() -> None:
    values = ExtendedIndicatorChoice((), (50,), ()).values(candles_of(wave(60, 9))).values

    assert {key.partition(".")[0] for key in values} == {"gann50"}


def test_windows_longer_than_the_history_are_declared_and_computed_on_it() -> None:
    choice = ExtendedIndicatorChoice((100, 200), (), (50,))

    computed = choice.values(candles_of(wave(60, 9)))

    assert computed.values["nota_storico"] == "storico di 60 candele, meno delle 100, 200 richieste"
    assert computed.values["fibonacci200.massimo"] == computed.values["fibonacci100.massimo"]
    assert computed.missing == ()


def test_a_dominant_cycle_without_two_periods_of_the_shortest_cycle_is_missing() -> None:
    computed = ExtendedIndicatorChoice((), (), (10,)).values(candles_of(wave(7, 4)))

    assert not [key for key in computed.values if key.startswith("ciclo10.")]
    assert computed.missing_note() == {"dati_mancanti": "ciclo10: storico di 7 candele"}


def test_a_dominant_cycle_holds_its_period_and_phase() -> None:
    assert DominantCycle(9, Decimal("12.5")) == DominantCycle(period=9, phase=Decimal("12.5"))
