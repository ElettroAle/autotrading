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


def test_the_extended_indicators_are_off_by_default_on_the_last_100_candles() -> None:
    assert [(p.key, p.label, p.default, p.minimum, p.maximum) for p in EXTENDED_PARAMETERS] == [
        ("fibonacci", "fibonacci", 0, 0, 1),
        ("gann", "gann", 0, 0, 1),
        ("ciclo", "ciclo", 0, 0, 1),
        ("candele_estese", "candele estese", 100, 10, 500),
    ]


def test_a_choice_reads_the_settings_and_the_defaults_for_what_they_do_not_say() -> None:
    assert ExtendedIndicatorChoice.of({"gann": 1, "candele_estese": 50}) == ExtendedIndicatorChoice(
        fibonacci=False, gann=True, cycle=False, candles=50
    )
    assert ExtendedIndicatorChoice.of({}) == ExtendedIndicatorChoice(
        fibonacci=False, gann=False, cycle=False, candles=100
    )


@pytest.mark.parametrize(
    ("settings", "asked", "needed"),
    [
        ({"fibonacci": 1, "candele_estese": 300}, 110, 300),
        ({"ciclo": 1, "candele_estese": 50}, 110, 110),
        ({"candele_estese": 300}, 110, 110),
    ],
)
def test_the_long_timeframe_reads_the_most_candles_between_those_asked_and_those_of_an_active_indicator(
    settings: dict[str, int], asked: int, needed: int
) -> None:
    assert ExtendedIndicatorChoice.of(settings).long_candles(asked) == needed


# Fibonacci


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


def test_no_extended_indicator_active_gives_no_value() -> None:
    assert ExtendedIndicatorChoice.of({}).values(candles_of(wave(100, 9))) == {}


def test_every_active_indicator_gives_its_values_on_the_last_candles_asked() -> None:
    candles = candles_of([Decimal(1000)] * 20 + wave(100, 9))
    choice = ExtendedIndicatorChoice(fibonacci=True, gann=True, cycle=True, candles=100)

    values = choice.values(candles)

    window = candles[-100:]
    assert values["candele_estese"] == Decimal(100)
    assert "nota_storico" not in values
    assert values["fibonacci.massimo"] == max(each.high for each in window)
    assert values["fibonacci.50%"] == fibonacci_levels(window)["50%"]
    angles = gann_angles(window)
    assert values["gann.perno"] == angles.pivot_side
    assert values["gann.prezzo_perno"] == angles.pivot
    assert values["gann.unita_per_candela"] == angles.unit
    assert values["gann.1x2"] == angles.lines["1x2"]
    assert values["ciclo.periodo_candele"] == Decimal(9)
    assert values["ciclo.fase_gradi"] == dominant_cycle(window).phase


def test_only_the_active_indicators_give_values() -> None:
    values = ExtendedIndicatorChoice(fibonacci=False, gann=True, cycle=False, candles=50).values(
        candles_of(wave(60, 9))
    )

    assert {key.partition(".")[0] for key in values} == {"candele_estese", "gann"}


def test_a_history_shorter_than_the_candles_asked_is_declared_and_used() -> None:
    choice = ExtendedIndicatorChoice(fibonacci=True, gann=False, cycle=False, candles=100)

    values = choice.values(candles_of(wave(60, 9)))

    assert values["nota_storico"] == "storico di 60 candele, meno delle 100 richieste"
    assert values["candele_estese"] == Decimal(60)


def test_a_dominant_cycle_holds_its_period_and_phase() -> None:
    assert DominantCycle(9, Decimal("12.5")) == DominantCycle(period=9, phase=Decimal("12.5"))
