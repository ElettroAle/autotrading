from collections.abc import Sequence
from dataclasses import dataclass

from autotrading.domain.sources.errors import TimeframeNotAvailableError

MINUTES_PER_HOUR = 60
MINUTES_PER_DAY = 24 * MINUTES_PER_HOUR


@dataclass(frozen=True, slots=True)
class Timeframe:
    """The span of one candle in minutes (R1.3.3); which spans exist is up to the exchange."""

    minutes: int

    @property
    def label(self) -> str:
        """The name the agent reads in its context, by the largest whole unit: 15m, 4h, 1d."""
        if self.minutes % MINUTES_PER_DAY == 0:
            return f"{self.minutes // MINUTES_PER_DAY}d"
        if self.minutes % MINUTES_PER_HOUR == 0:
            return f"{self.minutes // MINUTES_PER_HOUR}h"
        return f"{self.minutes}m"


LONG_TIMEFRAME = Timeframe(4 * MINUTES_PER_HOUR)


def short_timeframe_of(cycle_minutes: int, available: Sequence[Timeframe]) -> Timeframe:
    """The available timeframe of the cycle interval; between two of them, the finer one (ADR 0057, ADR 0083)."""
    finer = [timeframe for timeframe in available if timeframe.minutes <= cycle_minutes]
    if not finer:
        raise TimeframeNotAvailableError(cycle_minutes)
    return max(finer, key=lambda timeframe: timeframe.minutes)
