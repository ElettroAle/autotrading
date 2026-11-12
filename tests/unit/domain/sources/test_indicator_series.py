from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from autotrading.domain.sources.candle import Candle
from autotrading.domain.sources.errors import InsufficientHistoryError
from autotrading.domain.sources.indicator_series import indicator_series
from autotrading.domain.sources.technical_indicators import (
    exponential_moving_average,
    macd,
    relative_strength_index,
    simple_moving_average,
)
from autotrading.domain.sources.timeframe import LONG_TIMEFRAME, Timeframe, short_timeframe_of

START = datetime(2026, 11, 12, tzinfo=UTC)
CLOSES = [Decimal(100) + Decimal(index * index % 23) / 10 for index in range(120)]
CANDLES = [Candle(START + timedelta(minutes=15 * index), close, Decimal(index)) for index, close in enumerate(CLOSES)]


def test_the_short_timeframe_has_the_averages_of_20_the_macd_the_rsi_and_the_volume() -> None:
    series = indicator_series(CANDLES, 10, with_long_averages=False)

    assert list(series) == ["EMA20", "MA20", "MACD", "MACD_segnale", "MACD_istogramma", "RSI7", "RSI14", "volume"]
    assert series["EMA20"] == exponential_moving_average(CLOSES, 20)[-10:]
    assert series["MA20"] == simple_moving_average(CLOSES, 20)[-10:]
    assert series["MACD"] == [point.line for point in macd(CLOSES)][-10:]
    assert series["MACD_segnale"] == [point.signal for point in macd(CLOSES)][-10:]
    assert series["MACD_istogramma"] == [point.histogram for point in macd(CLOSES)][-10:]
    assert series["RSI7"] == relative_strength_index(CLOSES, 7)[-10:]
    assert series["RSI14"] == relative_strength_index(CLOSES, 14)[-10:]
    assert series["volume"] == [Decimal(index) for index in range(110, 120)]


def test_the_long_timeframe_adds_the_averages_of_50() -> None:
    series = indicator_series(CANDLES, 3, with_long_averages=True)

    assert series["EMA50"] == exponential_moving_average(CLOSES, 50)[-3:]
    assert series["MA50"] == simple_moving_average(CLOSES, 50)[-3:]
    assert all(len(values) == 3 for values in series.values())


def test_a_history_too_short_for_the_series_asked_is_insufficient() -> None:
    with pytest.raises(InsufficientHistoryError) as raised:
        indicator_series(CANDLES[:60], 30, with_long_averages=False)

    assert (raised.value.needed, raised.value.available) == (30, 27)


def test_a_history_too_short_for_an_indicator_is_insufficient() -> None:
    with pytest.raises(InsufficientHistoryError):
        indicator_series(CANDLES[:20], 1, with_long_averages=False)


@pytest.mark.parametrize(
    ("minutes", "label"),
    [(1, "1m"), (2, "1m"), (3, "3m"), (10, "5m"), (15, "15m"), (59, "30m"), (60, "1h"), (240, "4h"), (1440, "1d")],
)
def test_the_short_timeframe_is_the_cycle_interval_or_the_finer_one_below_it(minutes: int, label: str) -> None:
    assert short_timeframe_of(minutes).label == label


def test_the_long_timeframe_is_4_hours() -> None:
    assert Timeframe(240, "4h") == LONG_TIMEFRAME
