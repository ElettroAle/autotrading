from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from autotrading.domain.flows.errors import (
    BoundsOutsideRangeError,
    RangeBoundsRequiredError,
    RangeEndingBeforeStartError,
    UnknownStatisticsPeriodError,
)


class StatisticsPeriodKind(StrEnum):
    """The periods in the order the user chooses them, from the shortest (R6.4.6)."""

    LAST_30_MINUTES = "30m"
    LAST_HOUR = "1h"
    LAST_12_HOURS = "12h"
    LAST_24_HOURS = "24h"
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"
    ALL = "all"
    RANGE = "range"


LAST_DURATIONS = {
    StatisticsPeriodKind.LAST_30_MINUTES: timedelta(minutes=30),
    StatisticsPeriodKind.LAST_HOUR: timedelta(hours=1),
    StatisticsPeriodKind.LAST_12_HOURS: timedelta(hours=12),
    StatisticsPeriodKind.LAST_24_HOURS: timedelta(hours=24),
    StatisticsPeriodKind.LAST_7_DAYS: timedelta(days=7),
    StatisticsPeriodKind.LAST_30_DAYS: timedelta(days=30),
}
MINUTE = timedelta(minutes=1)


@dataclass(frozen=True, slots=True)
class TimeWindow:
    """The instants from `since` included to `until` excluded; a missing bound does not limit."""

    since: datetime | None = None
    until: datetime | None = None

    @classmethod
    def of_minutes(cls, since: datetime | None, until: datetime | None) -> TimeWindow:
        """The minutes from the one of `since` to the one of `until`, both whole (ADR periodo-al-minuto).

        An instant without a time zone is in UTC; a missing instant does not limit its side.
        """
        first = None if since is None else _minute_of(since)
        last = None if until is None else _minute_of(until)
        if first is not None and last is not None and first > last:
            raise RangeEndingBeforeStartError
        return cls(first, None if last is None else last + MINUTE)

    def contains(self, instant: datetime) -> bool:
        return (self.since is None or instant >= self.since) and (self.until is None or instant < self.until)


@dataclass(frozen=True, slots=True)
class StatisticsPeriod:
    """The period of the statistics of a flow: the whole life, the last minutes, hours or days, or a range (R2.2.6).

    A range holds its start and its end, both read to the minute (ADR periodo-al-minuto); a period of the last N holds
    the minutes from now less N to now (ADR periodi-brevi-come-durata-nel-dominio).
    """

    kind: StatisticsPeriodKind
    since: datetime | None = None
    until: datetime | None = None

    def __post_init__(self) -> None:
        is_range = self.kind is StatisticsPeriodKind.RANGE
        if not is_range and (self.since, self.until) != (None, None):
            raise BoundsOutsideRangeError
        if not is_range:
            return
        if self.since is None or self.until is None:
            raise RangeBoundsRequiredError
        TimeWindow.of_minutes(self.since, self.until)

    @classmethod
    def named(cls, name: str, since: datetime | None = None, until: datetime | None = None) -> StatisticsPeriod:
        kinds = {kind.value: kind for kind in StatisticsPeriodKind}
        if name not in kinds:
            raise UnknownStatisticsPeriodError(tuple(kinds))
        return cls(kinds[name], since, until)

    def window(self, now: datetime) -> TimeWindow:
        if self.kind in LAST_DURATIONS:
            return TimeWindow.of_minutes(now - LAST_DURATIONS[self.kind], now)
        return TimeWindow.of_minutes(self.since, self.until)


def _minute_of(instant: datetime) -> datetime:
    in_utc = instant.replace(tzinfo=UTC) if instant.tzinfo is None else instant.astimezone(UTC)
    return in_utc.replace(second=0, microsecond=0)
