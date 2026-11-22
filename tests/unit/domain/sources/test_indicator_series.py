from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from autotrading.domain.sources.candle import Candle
from autotrading.domain.sources.errors import InsufficientHistoryError, TimeframeNotAvailableError
from autotrading.domain.sources.indicator_series import (
    AVERAGE_PERIODS,
    RELATIVE_VOLUME_CANDLES,
    RSI_PERIODS,
    SERIES_LENGTH,
    WARM_UP,
    IndicatorChoice,
)
from autotrading.domain.sources.technical_indicators import (
    exponential_moving_average,
    macd,
    relative_strength_index,
    simple_moving_average,
)
from autotrading.domain.sources.timeframe import LONG_TIMEFRAME, Timeframe, short_timeframe_of

START = datetime(2026, 11, 12, tzinfo=UTC)
CLOSES = [Decimal(100) + Decimal(index * index % 23) / 10 for index in range(120)]
CANDLES = [
    Candle(START + timedelta(minutes=15 * index), close, Decimal(index), close + 1, close - 1)
    for index, close in enumerate(CLOSES)
]


def choice(
    length: int = 10,
    averages: tuple[int, ...] = (20, 50),
    rsi: tuple[int, ...] = (7, 14),
    volumes: tuple[int, ...] = (),
) -> IndicatorChoice:
    return IndicatorChoice(length, averages, rsi, volumes)


# The parameters


def test_the_periods_and_windows_are_lists_of_the_source_with_their_defaults() -> None:
    assert [
        (p.key, p.label, p.default, p.minimum, p.maximum, p.maximum_values)
        for p in (AVERAGE_PERIODS, RSI_PERIODS, RELATIVE_VOLUME_CANDLES)
    ] == [
        ("medie_periodi", "medie periodi", (20, 50), 2, 10000, 8),
        ("rsi_periodi", "rsi periodi", (7, 14), 2, 10000, 8),
        ("volume_relativo_candele", "volume relativo candele", (), 2, 10000, 8),
    ]
    assert (SERIES_LENGTH.key, SERIES_LENGTH.default, SERIES_LENGTH.minimum, SERIES_LENGTH.maximum) == (
        "lunghezza_serie",
        10,
        1,
        50,
    )


def test_a_choice_follows_the_settings_and_the_defaults() -> None:
    assert IndicatorChoice.of({"medie_periodi": (10, 200), "volume_relativo_candele": (42,)}) == choice(
        averages=(10, 200), volumes=(42,)
    )
    assert IndicatorChoice.of({}) == choice()


@pytest.mark.parametrize(
    ("chosen", "candles"),
    [
        (choice(), 10 + WARM_UP),
        (choice(averages=(200,)), 10 + 200),
        (choice(rsi=(150,)), 10 + 150),
        (choice(volumes=(500,)), 501),
        (choice(averages=(), rsi=()), 10 + WARM_UP),
    ],
)
def test_the_candles_read_cover_the_longest_period_over_the_series_and_the_longest_window(
    chosen: IndicatorChoice, candles: int
) -> None:
    assert chosen.candles == candles


# The series


def test_every_period_has_its_averages_and_every_rsi_period_its_index() -> None:
    series, computed = choice().values(CANDLES)

    assert list(series) == [
        "EMA20",
        "MA20",
        "EMA50",
        "MA50",
        "MACD",
        "MACD_segnale",
        "MACD_istogramma",
        "RSI7",
        "RSI14",
        "volume",
    ]
    assert series["EMA20"] == exponential_moving_average(CLOSES, 20)[-10:]
    assert series["MA20"] == simple_moving_average(CLOSES, 20)[-10:]
    assert series["EMA50"] == exponential_moving_average(CLOSES, 50)[-10:]
    assert series["MA50"] == simple_moving_average(CLOSES, 50)[-10:]
    assert series["MACD"] == [point.line for point in macd(CLOSES)][-10:]
    assert series["MACD_segnale"] == [point.signal for point in macd(CLOSES)][-10:]
    assert series["MACD_istogramma"] == [point.histogram for point in macd(CLOSES)][-10:]
    assert series["RSI7"] == relative_strength_index(CLOSES, 7)[-10:]
    assert series["RSI14"] == relative_strength_index(CLOSES, 14)[-10:]
    assert series["volume"] == [Decimal(index) for index in range(110, 120)]
    assert computed.values == {}
    assert computed.missing == ()


def test_the_series_have_the_length_asked() -> None:
    series, _ = choice(length=3).values(CANDLES)

    assert all(len(values) == 3 for values in series.values())


def test_no_period_means_no_average_and_no_rsi() -> None:
    series, _ = choice(averages=(), rsi=()).values(CANDLES)

    assert list(series) == ["MACD", "MACD_segnale", "MACD_istogramma", "volume"]


def test_a_period_the_history_cannot_give_over_the_whole_series_is_missing_and_the_others_arrive() -> None:
    series, computed = choice(averages=(20, 112), rsi=(7, 111)).values(CANDLES)

    assert {"EMA20", "MA20", "RSI7"} <= set(series)
    assert not {"EMA112", "MA112", "RSI111"} & set(series)
    assert computed.missing_note() == {"dati_mancanti": "EMA112, MA112, RSI111: storico di 120 candele"}


def test_the_longest_period_the_history_gives_over_the_whole_series_is_computed() -> None:
    series, computed = choice(averages=(111,), rsi=(110,)).values(CANDLES)

    assert {"EMA111", "MA111", "RSI110"} <= set(series)
    assert computed.missing == ()


def test_the_relative_volume_divides_the_last_volume_by_the_average_of_the_n_before() -> None:
    _, computed = choice(volumes=(4,)).values(CANDLES)

    # The volumes are the positions: 119 over the average of 115 to 118.
    assert computed.values == {"volume_relativo4": Decimal(119) / Decimal("116.5")}


def test_a_window_of_the_relative_volume_longer_than_the_history_is_missing() -> None:
    _, computed = choice(volumes=(4, 120)).values(CANDLES)

    assert set(computed.values) == {"volume_relativo4"}
    assert computed.missing_note() == {"dati_mancanti": "volume_relativo120: storico di 120 candele"}


def test_a_relative_volume_over_no_volume_is_missing() -> None:
    silent = [Candle(candle.closed_at, candle.close, Decimal(0), candle.high, candle.low) for candle in CANDLES]

    _, computed = choice(volumes=(4,)).values(silent)

    assert computed.missing_note() == {"dati_mancanti": "volume_relativo4: volume medio nullo"}


def test_a_history_too_short_for_the_series_asked_is_insufficient() -> None:
    with pytest.raises(InsufficientHistoryError) as raised:
        choice(length=30, averages=(), rsi=()).values(CANDLES[:60])

    assert (raised.value.needed, raised.value.available) == (30, 27)


def test_a_history_too_short_for_the_macd_is_insufficient() -> None:
    with pytest.raises(InsufficientHistoryError):
        choice(length=1, averages=(), rsi=()).values(CANDLES[:20])


# The intervals one exchange publishes, as its market data port declares them.
PUBLISHED = tuple(Timeframe(minutes) for minutes in (1, 3, 5, 15, 30, 60, 120, 240, 480, 720, 1440))


@pytest.mark.parametrize(
    ("minutes", "label"),
    [(1, "1m"), (2, "1m"), (3, "3m"), (10, "5m"), (15, "15m"), (59, "30m"), (60, "1h"), (240, "4h"), (1440, "1d")],
)
def test_the_short_timeframe_is_the_cycle_interval_or_the_finer_one_below_it(minutes: int, label: str) -> None:
    assert short_timeframe_of(minutes, PUBLISHED).label == label


def test_the_short_timeframe_does_not_depend_on_the_order_the_intervals_are_declared() -> None:
    assert short_timeframe_of(45, tuple(reversed(PUBLISHED))) == Timeframe(30)


def test_a_cycle_finer_than_every_published_interval_has_no_short_timeframe() -> None:
    with pytest.raises(TimeframeNotAvailableError) as raised:
        short_timeframe_of(3, (Timeframe(5), Timeframe(15)))

    assert raised.value.cycle_minutes == 3


@pytest.mark.parametrize(
    ("minutes", "label"),
    [(1, "1m"), (45, "45m"), (60, "1h"), (90, "90m"), (120, "2h"), (720, "12h"), (1440, "1d"), (4320, "3d")],
)
def test_a_timeframe_is_named_by_its_largest_whole_unit(minutes: int, label: str) -> None:
    assert Timeframe(minutes).label == label


def test_the_long_timeframe_is_4_hours() -> None:
    assert Timeframe(240) == LONG_TIMEFRAME
