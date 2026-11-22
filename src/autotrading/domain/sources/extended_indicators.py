"""Fibonacci retracements, Gann angles and the dominant cycle on the last candles of the long timeframe (R5.1.4).

Each one is a list of windows of the indicators source, empty by default, every window computed on the last N closed
candles; a history shorter than a window is declared and used as it is (ADR indicatori-estesi-nel-domain, ADR
parametri-delle-fonti-come-liste-libere).
"""

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from itertools import pairwise
from typing import Self

from autotrading.domain.sources.candle import Candle
from autotrading.domain.sources.computed_values import ComputedValues, MissingValue, short_history
from autotrading.domain.sources.errors import InsufficientHistoryError
from autotrading.domain.sources.source_list_parameter import MAXIMUM_CANDLES, SourceListParameter
from autotrading.domain.sources.source_parameter import SourceParameterValue

FIBONACCI_CANDLES = SourceListParameter("fibonacci_candele", "fibonacci candele", (), 10, MAXIMUM_CANDLES)
GANN_CANDLES = SourceListParameter("gann_candele", "gann candele", (), 10, MAXIMUM_CANDLES)
CYCLE_CANDLES = SourceListParameter("ciclo_candele", "ciclo candele", (), 10, MAXIMUM_CANDLES)
EXTENDED_PARAMETERS = (FIBONACCI_CANDLES, GANN_CANDLES, CYCLE_CANDLES)
HISTORY_NOTE = "nota_storico"
CANDLES = "candele"

FIBONACCI_RATIOS = (Decimal("0.236"), Decimal("0.382"), Decimal("0.5"), Decimal("0.618"), Decimal("0.786"))
# Price units per candle of each angle: 1x2 climbs one unit every two candles, 2x1 two units every candle.
GANN_RATES = {"1x1": Decimal(1), "1x2": Decimal("0.5"), "2x1": Decimal(2)}
LOW, HIGH = "minimo", "massimo"
SHORTEST_PERIOD = 4
# A period is recognised only if the history holds it at least twice.
CYCLES_IN_HISTORY = 2
FULL_TURN = Decimal(360)
PHASE_PLACES = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class GannAngles:
    """The angles from the most recent extreme, with the value of each line at the last closed candle."""

    pivot_side: str
    pivot: Decimal
    unit: Decimal
    lines: dict[str, Decimal]


@dataclass(frozen=True, slots=True)
class DominantCycle:
    """The period, in candles, of the strongest wave and its phase in degrees at the last candle: 0 is its peak."""

    period: int
    phase: Decimal


@dataclass(frozen=True, slots=True)
class ExtendedIndicatorChoice:
    """The windows, in candles, of each extended indicator the flow chose: none of any switches them off."""

    fibonacci: tuple[int, ...]
    gann: tuple[int, ...]
    cycle: tuple[int, ...]

    @classmethod
    def of(cls, settings: Mapping[str, SourceParameterValue]) -> Self:
        return cls(
            FIBONACCI_CANDLES.value_in(settings), GANN_CANDLES.value_in(settings), CYCLE_CANDLES.value_in(settings)
        )

    def long_candles(self, asked: int) -> int:
        """The candles of the long timeframe to read: a window counts only when it is longer than the series."""
        return max((asked, *self.fibonacci, *self.gann, *self.cycle))

    def values(self, candles: Sequence[Candle]) -> ComputedValues:
        """A series of values for every window of every indicator, named after the window."""
        computed = _history_note(candles, (*self.fibonacci, *self.gann, *self.cycle))
        for window in self.fibonacci:
            levels = fibonacci_levels(_window(candles, window))
            computed |= ComputedValues({f"fibonacci{window}.{name}": level for name, level in levels.items()})
        for window in self.gann:
            computed |= ComputedValues(_gann_values(f"gann{window}", gann_angles(_window(candles, window))))
        for window in self.cycle:
            computed |= _cycle_values(f"ciclo{window}", _window(candles, window))
        return computed


def fibonacci_levels(candles: Sequence[Candle]) -> dict[str, Decimal]:
    """The retracements from the highest high down towards the lowest low of the candles."""
    _require(candles, 1)
    low = min(candle.low for candle in candles)
    high = max(candle.high for candle in candles)
    levels = {f"{format((ratio * 100).normalize(), 'f')}%": high - ratio * (high - low) for ratio in FIBONACCI_RATIOS}
    return {LOW: low, HIGH: high, **levels}


def gann_angles(candles: Sequence[Candle]) -> GannAngles:
    """From the most recent extreme, one unit of price per candle is the average true range of the candles."""
    _require(candles, 1)
    low_at = _last_index_of(candles, min(candle.low for candle in candles), lambda candle: candle.low)
    high_at = _last_index_of(candles, max(candle.high for candle in candles), lambda candle: candle.high)
    unit = sum(_true_ranges(candles), Decimal(0)) / len(candles)
    if high_at > low_at:
        elapsed = len(candles) - 1 - high_at
        pivot = candles[high_at].high
        return GannAngles(HIGH, pivot, unit, {name: pivot - rate * unit * elapsed for name, rate in GANN_RATES.items()})
    elapsed = len(candles) - 1 - low_at
    pivot = candles[low_at].low
    return GannAngles(LOW, pivot, unit, {name: pivot + rate * unit * elapsed for name, rate in GANN_RATES.items()})


def dominant_cycle(candles: Sequence[Candle]) -> DominantCycle:
    """The peak of the periodogram of the closes without their least-squares line, over periods of 4 to N/2 candles.

    Sines and cosines exist only in binary floating point: the periodogram is computed there, the phase comes back as
    a decimal.
    """
    _require(candles, SHORTEST_PERIOD * CYCLES_IN_HISTORY)
    detrended = _detrended([float(candle.close) for candle in candles])
    periods = range(SHORTEST_PERIOD, len(detrended) // CYCLES_IN_HISTORY + 1)
    components = {period: _component(detrended, period) for period in periods}
    period = max(periods, key=lambda each: math.hypot(*components[each]))
    cosine, sine = components[period]
    last = len(detrended) - 1
    phase = math.degrees(2 * math.pi * last / period - math.atan2(sine, cosine)) % 360
    return DominantCycle(period, Decimal(phase).quantize(PHASE_PLACES) % FULL_TURN)


def _history_note(candles: Sequence[Candle], windows: tuple[int, ...]) -> ComputedValues:
    """The windows longer than the history, computed on the candles there are, say so."""
    longer = sorted({window for window in windows if window > len(candles)})
    if not longer:
        return ComputedValues()
    asked = ", ".join(str(window) for window in longer)
    return ComputedValues({HISTORY_NOTE: f"storico di {len(candles)} candele, meno delle {asked} richieste"})


def _window(candles: Sequence[Candle], window: int) -> list[Candle]:
    return list(candles[-window:])


def _gann_values(name: str, angles: GannAngles) -> dict[str, Decimal | str]:
    values: dict[str, Decimal | str] = {
        f"{name}.perno": angles.pivot_side,
        f"{name}.prezzo_perno": angles.pivot,
        f"{name}.unita_per_candela": angles.unit,
    }
    return values | {f"{name}.{angle}": line for angle, line in angles.lines.items()}


def _cycle_values(name: str, candles: list[Candle]) -> ComputedValues:
    """The dominant cycle needs a period seen twice: a shorter history is declared missing."""
    if len(candles) < SHORTEST_PERIOD * CYCLES_IN_HISTORY:
        return ComputedValues(missing=(MissingValue(name, short_history(len(candles), CANDLES)),))
    cycle = dominant_cycle(candles)
    return ComputedValues({f"{name}.periodo_candele": Decimal(cycle.period), f"{name}.fase_gradi": cycle.phase})


def _last_index_of(candles: Sequence[Candle], extreme: Decimal, price: Callable[[Candle], Decimal]) -> int:
    return max(index for index, candle in enumerate(candles) if price(candle) == extreme)


def _true_ranges(candles: Sequence[Candle]) -> list[Decimal]:
    first = candles[0]
    ranges = [first.high - first.low]
    for previous, current in pairwise(candles):
        ranges.append(
            max(current.high - current.low, abs(current.high - previous.close), abs(current.low - previous.close))
        )
    return ranges


def _detrended(closes: list[float]) -> list[float]:
    count = len(closes)
    middle = (count - 1) / 2
    mean = sum(closes) / count
    slope = sum((index - middle) * (close - mean) for index, close in enumerate(closes)) / sum(
        (index - middle) ** 2 for index in range(count)
    )
    return [close - mean - slope * (index - middle) for index, close in enumerate(closes)]


def _component(values: list[float], period: int) -> tuple[float, float]:
    """The cosine and sine sums of the values at the frequency of the period."""
    angle = 2 * math.pi / period
    cosine = sum(value * math.cos(angle * index) for index, value in enumerate(values))
    sine = sum(value * math.sin(angle * index) for index, value in enumerate(values))
    return cosine, sine


def _require(candles: Sequence[Candle], needed: int) -> None:
    if len(candles) < needed:
        raise InsufficientHistoryError(needed, len(candles))
