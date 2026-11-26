"""The regime data of the indicators (R5.5.4): where the price stands against the low and the high of the last hours,
its change over hours and the series of the closes of the two timeframes, each switched on by a parameter of the adapter
of the market; the hourly values are computed on the closed hourly candles, and a value the history cannot give is
declared among the missing data while the others arrive (ADR dati-di-regime-nella-fonte-indicatori).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Self

from autotrading.domain.sources.candle import Candle
from autotrading.domain.sources.computed_values import ComputedValues, MissingValue, short_history
from autotrading.domain.sources.errors import TimeframeNotAvailableError
from autotrading.domain.sources.source_list_parameter import SourceListParameter
from autotrading.domain.sources.source_parameter import SourceParameter, SourceParameterValue
from autotrading.domain.sources.technical_indicators import last_values
from autotrading.domain.sources.timeframe import MINUTES_PER_HOUR, Timeframe

# Thirty days of hours: the longest window the requirement admits.
MAXIMUM_HOURS = 720
HOURLY_TIMEFRAME = Timeframe(MINUTES_PER_HOUR)
HOURS = "candele orarie"
EXTREMES_PREFIX, CHANGES_PREFIX = "estremi.", "tendenza."
EXTREME_VALUES = ("minimo", "massimo", "dal_minimo", "dal_massimo")
# The name of the closes among the series of a timeframe: the agent reads them as "<timeframe>.chiusura.serie".
CLOSE_SERIES_NAME = "chiusura"
HUNDRED = Decimal(100)


def _hours(key: str) -> SourceListParameter:
    return SourceListParameter(key, key, (), 1, MAXIMUM_HOURS, range_reason=f"{key} va da 1 a {MAXIMUM_HOURS}")


EXTREMES_HOURS = _hours("estremi_ore")
CHANGE_HOURS = _hours("variazione_ore")
CLOSE_SERIES = SourceParameter(
    "serie_chiusure", "serie_chiusure", 0, 0, 1, range_reason="serie_chiusure vale 0 oppure 1"
)
# The parameters the adapter of the market declares for the indicators, beside those of the source.
REGIME_PARAMETERS = (EXTREMES_HOURS, CHANGE_HOURS, CLOSE_SERIES)


@dataclass(frozen=True, slots=True)
class RegimeChoice:
    """The windows of the extremes, the hours of the changes and the series of the closes the flow chose: none of them
    gives the values of the indicators of before.
    """

    extremes: tuple[int, ...]
    changes: tuple[int, ...]
    close_series: bool

    @classmethod
    def of(cls, settings: Mapping[str, SourceParameterValue]) -> Self:
        return cls(
            EXTREMES_HOURS.value_in(settings), CHANGE_HOURS.value_in(settings), CLOSE_SERIES.value_in(settings) == 1
        )

    @property
    def reads_hourly_candles(self) -> bool:
        return bool(self.extremes or self.changes)

    @property
    def hourly_candles(self) -> int:
        """The candles the longest value needs: the window of the extremes, or the close N hours before the last one."""
        return max(max(self.extremes, default=0), max(self.changes, default=-1) + 1)

    def hourly_values(self, candles: Sequence[Candle], price: Decimal) -> ComputedValues:
        """The extremes and the changes on the closed hourly candles, oldest first, against the price of now."""
        return self._extremes(candles, price).prefixed(EXTREMES_PREFIX) | self._changes(candles, price).prefixed(
            CHANGES_PREFIX
        )

    def closes(self, candles: Sequence[Candle], length: int) -> dict[str, list[Decimal]]:
        """The closes of the last candles of a timeframe, as many as the series of the flow, oldest first."""
        if not self.close_series:
            return {}
        return {CLOSE_SERIES_NAME: last_values([candle.close for candle in candles], length)}

    def _extremes(self, candles: Sequence[Candle], price: Decimal) -> ComputedValues:
        """The lowest low and the highest high of the last N candles, and how far the price stands from them."""
        values: dict[str, Decimal | str] = {}
        missing: list[MissingValue] = []
        for hours in self.extremes:
            if len(candles) < hours:
                reason = short_history(len(candles), HOURS)
                missing.extend(MissingValue(f"{name}_{hours}h", reason) for name in EXTREME_VALUES)
                continue
            window = candles[-hours:]
            low, high = min(candle.low for candle in window), max(candle.high for candle in window)
            values |= {
                f"minimo_{hours}h": low,
                f"massimo_{hours}h": high,
                f"dal_minimo_{hours}h": _change(price, low),
                f"dal_massimo_{hours}h": _change(price, high),
            }
        return ComputedValues(values, tuple(missing))

    def _changes(self, candles: Sequence[Candle], price: Decimal) -> ComputedValues:
        """The change of the price from the close of N hours ago, the one N candles before the last."""
        values: dict[str, Decimal | str] = {}
        missing: list[MissingValue] = []
        for hours in self.changes:
            name = f"variazione_{hours}h"
            if len(candles) <= hours:
                missing.append(MissingValue(name, short_history(len(candles), HOURS)))
                continue
            values[name] = _change(price, candles[-1 - hours].close)
        return ComputedValues(values, tuple(missing))


def hourly_timeframe_of(available: Sequence[Timeframe]) -> Timeframe:
    """The hourly timeframe, if the market publishes it: without it no value on the hours can be read."""
    if HOURLY_TIMEFRAME not in available:
        raise TimeframeNotAvailableError(HOURLY_TIMEFRAME.minutes)
    return HOURLY_TIMEFRAME


def _change(price: Decimal, reference: Decimal) -> Decimal:
    """How far the price stands from the reference, in percent of the reference."""
    return (price - reference) / reference * HUNDRED
