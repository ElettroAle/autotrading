"""The series of indicators of one timeframe, the last values the flow asks for, oldest first (R1.3.3), with the periods
of the averages and of the RSI and the windows of the relative volume the flow chose (ADR
parametri-delle-fonti-come-liste-libere).
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Self

from autotrading.domain.sources.candle import Candle
from autotrading.domain.sources.computed_values import ComputedValues, MissingValue, short_history
from autotrading.domain.sources.errors import InsufficientHistoryError
from autotrading.domain.sources.source_list_parameter import MAXIMUM_CANDLES, SourceListParameter
from autotrading.domain.sources.source_parameter import SourceParameter, SourceParameterValue
from autotrading.domain.sources.technical_indicators import (
    exponential_moving_average,
    last_values,
    macd,
    relative_strength_index,
    simple_moving_average,
)

SERIES_LENGTH = SourceParameter(
    "lunghezza_serie",
    "lunghezza serie",
    default=10,
    minimum=1,
    maximum=50,
    description=(
        "Quanti valori recenti di ogni indicatore riceve l'agente, dal più vecchio al più nuovo. Da 1 a 50. "
        "Predefinito: 10."
    ),
)
AVERAGE_PERIODS = SourceListParameter(
    "medie_periodi",
    "medie periodi",
    (20, 50),
    2,
    MAXIMUM_CANDLES,
    description=(
        "Periodi in candele delle medie mobili, esponenziale e semplice, una per periodo. Da 2 a 10000, al massimo 8 "
        "valori. Predefinito: 20, 50; vuoto: nessuna media."
    ),
)
RSI_PERIODS = SourceListParameter(
    "rsi_periodi",
    "rsi periodi",
    (7, 14),
    2,
    MAXIMUM_CANDLES,
    description=(
        "Periodi in candele dell'RSI, uno per periodo. Da 2 a 10000, al massimo 8 valori. Predefinito: 7, 14; vuoto: "
        "nessun RSI."
    ),
)
RELATIVE_VOLUME_CANDLES = SourceListParameter(
    "volume_relativo_candele",
    "volume relativo candele",
    (),
    2,
    MAXIMUM_CANDLES,
    description=(
        "Candele con cui si confronta il volume dell'ultima candela chiusa: il volume relativo è il suo rapporto con "
        "la media di quelle candele. Da 2 a 10000, al massimo 8 valori. Vuoto: nessun volume relativo."
    ),
)
# The MACD needs history before its first value: the exchange is asked for at least this many more candles.
WARM_UP = 100
CANDLES = "candele"
NO_VOLUME = "volume medio nullo"

type Series = dict[str, list[Decimal]]
type Indicator = Callable[[Sequence[Decimal], int], list[Decimal]]


@dataclass(frozen=True, slots=True)
class IndicatorChoice:
    """How long the series are and which periods and windows the flow chose, for both timeframes."""

    length: int
    averages: tuple[int, ...]
    rsi_periods: tuple[int, ...]
    volume_windows: tuple[int, ...]

    @classmethod
    def of(cls, settings: Mapping[str, SourceParameterValue]) -> Self:
        return cls(
            SERIES_LENGTH.value_in(settings),
            AVERAGE_PERIODS.value_in(settings),
            RSI_PERIODS.value_in(settings),
            RELATIVE_VOLUME_CANDLES.value_in(settings),
        )

    @property
    def candles(self) -> int:
        """The candles to read: enough for the longest period over the whole series, and for the longest window of
        the relative volume before the last candle.
        """
        longest_period = max((*self.averages, *self.rsi_periods), default=0)
        longest_window = max(self.volume_windows, default=0)
        return max(self.length + max(WARM_UP, longest_period), longest_window + 1)

    def values(self, candles: Sequence[Candle]) -> tuple[Series, ComputedValues]:
        """The series of the timeframe, then its relative volumes with the values its history cannot give."""
        closes = [candle.close for candle in candles]
        points = macd(closes)
        averages, missing_averages = self._periods(
            closes, {"EMA": exponential_moving_average, "MA": simple_moving_average}, self.averages, 0
        )
        rsi, missing_rsi = self._periods(closes, {"RSI": relative_strength_index}, self.rsi_periods, 1)
        series = {
            **averages,
            "MACD": [point.line for point in points],
            "MACD_segnale": [point.signal for point in points],
            "MACD_istogramma": [point.histogram for point in points],
            **rsi,
            "volume": [candle.volume for candle in candles],
        }
        lasts = {name: _last(values, self.length) for name, values in series.items()}
        return lasts, ComputedValues(missing=(*missing_averages, *missing_rsi)) | self._relative_volumes(candles)

    def _periods(
        self, closes: list[Decimal], indicators: Mapping[str, Indicator], periods: tuple[int, ...], extra: int
    ) -> tuple[Series, list[MissingValue]]:
        """Each indicator over each period whose whole series the history holds; the others are missing. An average
        of P closes has its first value at the P-th close, an RSI one close later.
        """
        series: Series = {}
        missing: list[MissingValue] = []
        for period in periods:
            computable = len(closes) >= period - 1 + extra + self.length
            for name, indicator in indicators.items():
                if computable:
                    series[f"{name}{period}"] = indicator(closes, period)
                else:
                    missing.append(MissingValue(f"{name}{period}", short_history(len(closes), CANDLES)))
        return series, missing

    def _relative_volumes(self, candles: Sequence[Candle]) -> ComputedValues:
        """The volume of the last closed candle divided by the average of the N before it."""
        values: dict[str, Decimal | str] = {}
        missing: list[MissingValue] = []
        for window in self.volume_windows:
            name = f"volume_relativo{window}"
            if len(candles) <= window:
                missing.append(MissingValue(name, short_history(len(candles), CANDLES)))
                continue
            average = sum((candle.volume for candle in candles[-1 - window : -1]), Decimal(0)) / window
            if average == 0:
                missing.append(MissingValue(name, NO_VOLUME))
                continue
            values[name] = candles[-1].volume / average
        return ComputedValues(values, tuple(missing))


def _last(values: list[Decimal], length: int) -> list[Decimal]:
    if len(values) < length:
        raise InsufficientHistoryError(length, len(values))
    return last_values(values, length)
