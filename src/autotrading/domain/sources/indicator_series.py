"""The series of indicators of one timeframe, the last values the flow asks for, oldest first (R1.3.3)."""

from collections.abc import Sequence
from decimal import Decimal

from autotrading.domain.sources.candle import Candle
from autotrading.domain.sources.errors import InsufficientHistoryError
from autotrading.domain.sources.technical_indicators import (
    exponential_moving_average,
    last_values,
    macd,
    relative_strength_index,
    simple_moving_average,
)

SHORT_PERIOD, LONG_PERIOD = 20, 50
FAST_RSI, SLOW_RSI = 7, 14
# The averages and the MACD need history before their first value: the exchange is asked for this many more candles.
WARM_UP = 100


def indicator_series(
    candles: Sequence[Candle], length: int, *, with_long_averages: bool
) -> dict[str, list[Decimal]]:
    closes = [candle.close for candle in candles]
    points = macd(closes)
    series = {
        "EMA20": exponential_moving_average(closes, SHORT_PERIOD),
        "MA20": simple_moving_average(closes, SHORT_PERIOD),
        "MACD": [point.line for point in points],
        "MACD_segnale": [point.signal for point in points],
        "MACD_istogramma": [point.histogram for point in points],
        "RSI7": relative_strength_index(closes, FAST_RSI),
        "RSI14": relative_strength_index(closes, SLOW_RSI),
        "volume": [candle.volume for candle in candles],
    }
    if with_long_averages:
        series["EMA50"] = exponential_moving_average(closes, LONG_PERIOD)
        series["MA50"] = simple_moving_average(closes, LONG_PERIOD)
    return {name: _last(values, length) for name, values in series.items()}


def _last(values: list[Decimal], length: int) -> list[Decimal]:
    if len(values) < length:
        raise InsufficientHistoryError(length, len(values))
    return last_values(values, length)
