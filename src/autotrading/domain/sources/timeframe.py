from dataclasses import dataclass

MINUTES_PER_HOUR = 60


@dataclass(frozen=True, slots=True)
class Timeframe:
    """The span of one candle, as the exchanges name it (R1.3.3)."""

    minutes: int
    label: str


# The candle intervals the exchanges publish, from the finest: a cycle interval in between takes the one below it.
TIMEFRAMES = tuple(
    Timeframe(minutes, label)
    for minutes, label in (
        (1, "1m"),
        (3, "3m"),
        (5, "5m"),
        (15, "15m"),
        (30, "30m"),
        (60, "1h"),
        (120, "2h"),
        (240, "4h"),
        (480, "8h"),
        (720, "12h"),
        (1440, "1d"),
    )
)
LONG_TIMEFRAME = Timeframe(240, "4h")


def short_timeframe_of(cycle_minutes: int) -> Timeframe:
    """The timeframe of the cycle interval; between two intervals of the exchange, the finer one (ADR 0057)."""
    return [timeframe for timeframe in TIMEFRAMES if timeframe.minutes <= cycle_minutes][-1]
