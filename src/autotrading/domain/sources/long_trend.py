"""The trend over several days on the closed UTC daily candles of the market (R5.1.6).

The changes of the price over the days and the channels of the closes the flow chose, each a list of the indicators
source, and the last daily close with its instant; a value without enough history is declared among the missing data
and the others arrive (ADR parametri-delle-fonti-come-liste-libere).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC
from decimal import Decimal
from typing import Self

from autotrading.domain.sources.candle import Candle
from autotrading.domain.sources.computed_values import ComputedValues, MissingValue, short_history
from autotrading.domain.sources.errors import TimeframeNotAvailableError
from autotrading.domain.sources.source_list_parameter import MAXIMUM_DAYS, SourceListParameter
from autotrading.domain.sources.source_parameter import SourceParameterValue
from autotrading.domain.sources.timeframe import MINUTES_PER_DAY, Timeframe

TREND_DAYS = SourceListParameter(
    "tendenza_giorni",
    "tendenza giorni",
    (),
    1,
    MAXIMUM_DAYS,
    description=(
        "Giorni della variazione percentuale tra l'ultima chiusura giornaliera e quella di tanti giorni prima, una "
        "per valore. Da 1 a 3650, al massimo 8 valori. Vuoto: nessuna variazione a giorni."
    ),
)
CHANNEL_DAYS = SourceListParameter(
    "canale_giorni",
    "canale giorni",
    (),
    2,
    MAXIMUM_DAYS,
    description=(
        "Giorni del canale: massimo, minimo e punto medio delle chiusure giornaliere di quei giorni, uno per valore. "
        "Da 2 a 3650, al massimo 8 valori. Vuoto: nessun canale."
    ),
)
DAILY_TIMEFRAME = Timeframe(MINUTES_PER_DAY)
PREFIX = "tendenza."
LAST_CLOSE, LAST_CLOSE_AT = "ultima_chiusura", "ultima_chiusura_istante"
DAYS = "giorni chiusi"
TWO = Decimal(2)


@dataclass(frozen=True, slots=True)
class LongTrendChoice:
    """The days of the changes and of the channels the flow chose: none of either switches the trend off."""

    days: tuple[int, ...]
    channels: tuple[int, ...]

    @classmethod
    def of(cls, settings: Mapping[str, SourceParameterValue]) -> Self:
        return cls(TREND_DAYS.value_in(settings), CHANNEL_DAYS.value_in(settings))

    @property
    def active(self) -> bool:
        return bool(self.days or self.channels)

    @property
    def daily_candles(self) -> int:
        """The candles the longest value needs: the last close and the N days before it."""
        return max((*self.days, *self.channels), default=0) + 1

    def values(self, candles: Sequence[Candle]) -> ComputedValues:
        """The values of the trend on the closed daily candles, oldest first, and the ones the history cannot give."""
        computed = self._changes(candles) | self._channels(candles) | _last_close(candles)
        return computed.prefixed(PREFIX)

    def _changes(self, candles: Sequence[Candle]) -> ComputedValues:
        """The change from the close N days before the last one to the last one, in percent."""
        values: dict[str, Decimal | str] = {}
        missing: list[MissingValue] = []
        for days in self.days:
            name = f"variazione_{days}g"
            if len(candles) <= days:
                missing.append(MissingValue(name, short_history(len(candles), DAYS)))
                continue
            values[name] = (candles[-1].close / candles[-1 - days].close - 1) * 100
        return ComputedValues(values, tuple(missing))

    def _channels(self, candles: Sequence[Candle]) -> ComputedValues:
        """Highest, lowest and middle of the closes of the N days before the last one."""
        values: dict[str, Decimal | str] = {}
        missing: list[MissingValue] = []
        for days in self.channels:
            if len(candles) <= days:
                missing.append(MissingValue(f"canale_{days}g", short_history(len(candles), DAYS)))
                continue
            previous = [candle.close for candle in candles[-1 - days : -1]]
            high, low = max(previous), min(previous)
            values |= {f"massimo_{days}g": high, f"minimo_{days}g": low, f"punto_medio_{days}g": (high + low) / TWO}
        return ComputedValues(values, tuple(missing))


def daily_timeframe_of(available: Sequence[Timeframe]) -> Timeframe:
    """The daily timeframe, if the market publishes it: without it no value on the days can be read."""
    if DAILY_TIMEFRAME not in available:
        raise TimeframeNotAvailableError(DAILY_TIMEFRAME.minutes)
    return DAILY_TIMEFRAME


def _last_close(candles: Sequence[Candle]) -> ComputedValues:
    if not candles:
        return ComputedValues(missing=(MissingValue(LAST_CLOSE, short_history(0, DAYS)),))
    last = candles[-1]
    return ComputedValues({LAST_CLOSE: last.close, LAST_CLOSE_AT: last.closed_at.astimezone(UTC).isoformat()})
