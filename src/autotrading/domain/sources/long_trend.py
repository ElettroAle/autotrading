"""The trend over several days on the closed UTC daily candles of the market (R5.1.6).

Behind a parameter of the indicators source, off by default: the change of the price over 7, 14, 30 and 60 days, the
channel of the closes of the 20 days before the last one and the last daily close with its instant; a value without
enough history is declared among the values of the source (ADR tendenza-lunga-sulle-candele-giornaliere).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC
from decimal import Decimal
from typing import Self

from autotrading.domain.sources.candle import Candle
from autotrading.domain.sources.errors import TimeframeNotAvailableError
from autotrading.domain.sources.source_parameter import SourceParameter
from autotrading.domain.sources.timeframe import MINUTES_PER_DAY, Timeframe

LONG_TREND = SourceParameter("tendenza_lunga", "tendenza lunga", default=0, minimum=0, maximum=1)
DAILY_TIMEFRAME = Timeframe(MINUTES_PER_DAY)
HORIZON_DAYS = (7, 14, 30, 60)
CHANNEL_DAYS = 20
# The longest change compares the last close with the one 60 candles before it.
DAILY_CANDLES = max(HORIZON_DAYS) + 1
PREFIX = "tendenza."
HIGH, LOW = "massimo_20g", "minimo_20g"
LAST_CLOSE, LAST_CLOSE_AT = "ultima_chiusura", "ultima_chiusura_istante"
MISSING = "dati_mancanti"


@dataclass(frozen=True, slots=True)
class LongTrendChoice:
    """Whether the flow switched the trend over several days on."""

    active: bool

    @classmethod
    def of(cls, settings: Mapping[str, int]) -> Self:
        return cls(active=settings.get(LONG_TREND.key, LONG_TREND.default) == 1)


def daily_timeframe_of(available: Sequence[Timeframe]) -> Timeframe:
    """The daily timeframe, if the market publishes it: without it the trend cannot be read."""
    if DAILY_TIMEFRAME not in available:
        raise TimeframeNotAvailableError(DAILY_TIMEFRAME.minutes)
    return DAILY_TIMEFRAME


def long_trend(candles: Sequence[Candle]) -> dict[str, Decimal | str]:
    """The values of the trend on the closed daily candles, oldest first, and the ones the history cannot give."""
    values = {**_changes(candles), **_channel(candles), **_last_close(candles)}
    missing = [name for name in _every_name() if name not in values]
    if missing:
        values[MISSING] = f"{', '.join(missing)}: storico di {len(candles)} giorni chiusi"
    return {f"{PREFIX}{name}": value for name, value in values.items()}


def _changes(candles: Sequence[Candle]) -> dict[str, Decimal | str]:
    return {
        _change_name(days): (candles[-1].close / candles[-1 - days].close - 1) * 100
        for days in HORIZON_DAYS
        if len(candles) > days
    }


def _channel(candles: Sequence[Candle]) -> dict[str, Decimal | str]:
    if len(candles) <= CHANNEL_DAYS:
        return {}
    previous = [candle.close for candle in candles[-1 - CHANNEL_DAYS : -1]]
    return {HIGH: max(previous), LOW: min(previous)}


def _last_close(candles: Sequence[Candle]) -> dict[str, Decimal | str]:
    if not candles:
        return {}
    last = candles[-1]
    return {LAST_CLOSE: last.close, LAST_CLOSE_AT: last.closed_at.astimezone(UTC).isoformat()}


def _every_name() -> list[str]:
    return [*(_change_name(days) for days in HORIZON_DAYS), HIGH, LOW, LAST_CLOSE]


def _change_name(days: int) -> str:
    return f"variazione_{days}g"
