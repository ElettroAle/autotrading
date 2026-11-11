"""Technical indicators computed on the prices of the exchange of the flow, in exact decimals (R1.3.3).

Every function returns the whole series it can compute, oldest first: the source keeps the last values the flow
asks for. A history too short for an indicator raises InsufficientHistoryError.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from itertools import pairwise

from autotrading.domain.sources.errors import InsufficientHistoryError

HUNDRED = Decimal(100)
MACD_FAST, MACD_SLOW, MACD_SIGNAL = 12, 26, 9


@dataclass(frozen=True, slots=True)
class MacdPoint:
    line: Decimal
    signal: Decimal
    histogram: Decimal


def simple_moving_average(values: Sequence[Decimal], period: int) -> list[Decimal]:
    _require_history(values, period)
    window = sum(values[:period], Decimal(0))
    averages = [window / period]
    for index in range(period, len(values)):
        window += values[index] - values[index - period]
        averages.append(window / period)
    return averages


def exponential_moving_average(values: Sequence[Decimal], period: int) -> list[Decimal]:
    """Seeded with the simple average of the first period, then smoothed by 2 / (period + 1)."""
    _require_history(values, period)
    smoothing = Decimal(2) / (period + 1)
    averages = [sum(values[:period], Decimal(0)) / period]
    for value in values[period:]:
        averages.append(averages[-1] + smoothing * (value - averages[-1]))
    return averages


def macd(values: Sequence[Decimal]) -> list[MacdPoint]:
    """EMA12 minus EMA26, its EMA9 as signal, and their difference as histogram."""
    _require_history(values, MACD_SLOW + MACD_SIGNAL - 1)
    fast = exponential_moving_average(values, MACD_FAST)[MACD_SLOW - MACD_FAST :]
    slow = exponential_moving_average(values, MACD_SLOW)
    lines = [fast_value - slow_value for fast_value, slow_value in zip(fast, slow, strict=True)]
    signals = exponential_moving_average(lines, MACD_SIGNAL)
    aligned = lines[MACD_SIGNAL - 1 :]
    return [MacdPoint(line, signal, line - signal) for line, signal in zip(aligned, signals, strict=True)]


def relative_strength_index(values: Sequence[Decimal], period: int) -> list[Decimal]:
    """Wilder's RSI: average gain and loss of the first period, then smoothed by (period - 1) / period."""
    _require_history(values, period + 1)
    changes = [current - previous for previous, current in pairwise(values)]
    gain = sum((max(change, Decimal(0)) for change in changes[:period]), Decimal(0)) / period
    loss = sum((max(-change, Decimal(0)) for change in changes[:period]), Decimal(0)) / period
    indexes = [_rsi(gain, loss)]
    for change in changes[period:]:
        gain = (gain * (period - 1) + max(change, Decimal(0))) / period
        loss = (loss * (period - 1) + max(-change, Decimal(0))) / period
        indexes.append(_rsi(gain, loss))
    return indexes


def last_values[T](series: Sequence[T], count: int) -> list[T]:
    """The most recent values of a series, oldest first."""
    return list(series[-count:])


def _rsi(gain: Decimal, loss: Decimal) -> Decimal:
    if loss == 0:
        return HUNDRED if gain > 0 else HUNDRED / 2
    return HUNDRED - HUNDRED / (1 + gain / loss)


def _require_history(values: Sequence[Decimal], needed: int) -> None:
    if len(values) < needed:
        raise InsufficientHistoryError(needed, len(values))
