"""Fibonacci retracements, Gann angles and the dominant cycle on the last candles of the long timeframe (R5.1.4).

Each one is a parameter of the indicators source, off by default, computed on the last N closed candles; a history
shorter than N is declared and used as it is (ADR indicatori-estesi-nel-domain).
"""

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from itertools import pairwise
from typing import Self

from autotrading.domain.sources.candle import Candle
from autotrading.domain.sources.errors import InsufficientHistoryError
from autotrading.domain.sources.source_parameter import SourceParameter

FIBONACCI = SourceParameter("fibonacci", "fibonacci", default=0, minimum=0, maximum=1)
GANN = SourceParameter("gann", "gann", default=0, minimum=0, maximum=1)
CYCLE = SourceParameter("ciclo", "ciclo", default=0, minimum=0, maximum=1)
EXTENDED_CANDLES = SourceParameter("candele_estese", "candele estese", default=100, minimum=10, maximum=500)
EXTENDED_PARAMETERS = (FIBONACCI, GANN, CYCLE, EXTENDED_CANDLES)

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
    """The extended indicators a flow switched on, and how many candles they read."""

    fibonacci: bool
    gann: bool
    cycle: bool
    candles: int

    @classmethod
    def of(cls, settings: Mapping[str, int]) -> Self:
        def setting(parameter: SourceParameter) -> int:
            return settings.get(parameter.key, parameter.default)

        return cls(
            fibonacci=setting(FIBONACCI) == 1,
            gann=setting(GANN) == 1,
            cycle=setting(CYCLE) == 1,
            candles=setting(EXTENDED_CANDLES),
        )

    @property
    def active(self) -> bool:
        return self.fibonacci or self.gann or self.cycle

    def long_candles(self, asked: int) -> int:
        """The candles of the long timeframe to read: N counts only when an extended indicator needs them."""
        if not self.active:
            return asked
        return max(asked, self.candles)

    def values(self, candles: Sequence[Candle]) -> dict[str, Decimal | str]:
        if not self.active:
            return {}
        window = list(candles[-self.candles :])
        values: dict[str, Decimal | str] = {"candele_estese": Decimal(len(window))}
        if len(window) < self.candles:
            values["nota_storico"] = f"storico di {len(window)} candele, meno delle {self.candles} richieste"
        if self.fibonacci:
            values |= {f"fibonacci.{name}": level for name, level in fibonacci_levels(window).items()}
        if self.gann:
            values |= _gann_values(gann_angles(window))
        if self.cycle:
            cycle = dominant_cycle(window)
            values |= {"ciclo.periodo_candele": Decimal(cycle.period), "ciclo.fase_gradi": cycle.phase}
        return values


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


def _gann_values(angles: GannAngles) -> dict[str, Decimal | str]:
    values: dict[str, Decimal | str] = {
        "gann.perno": angles.pivot_side,
        "gann.prezzo_perno": angles.pivot,
        "gann.unita_per_candela": angles.unit,
    }
    return values | {f"gann.{name}": line for name, line in angles.lines.items()}


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
