from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum

from autotrading.domain.flows.errors import (
    DaysOutsideRangeError,
    RangeDaysRequiredError,
    RangeEndingBeforeStartError,
    UnknownStatisticsPeriodError,
)


class StatisticsPeriodKind(StrEnum):
    ALL = "all"
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"
    RANGE = "range"


LAST_DAYS = {StatisticsPeriodKind.LAST_7_DAYS: 7, StatisticsPeriodKind.LAST_30_DAYS: 30}


@dataclass(frozen=True, slots=True)
class TimeWindow:
    """The instants from `since` included to `until` excluded; a missing bound does not limit."""

    since: datetime | None = None
    until: datetime | None = None

    def contains(self, instant: datetime) -> bool:
        return (self.since is None or instant >= self.since) and (self.until is None or instant < self.until)


@dataclass(frozen=True, slots=True)
class StatisticsPeriod:
    """The period of the statistics of a flow: the whole life, the last 7 or 30 days, or a range of days (R2.2.6).

    A range holds its first and last day, both whole, in UTC.
    """

    kind: StatisticsPeriodKind
    first_day: date | None = None
    last_day: date | None = None

    def __post_init__(self) -> None:
        is_range = self.kind is StatisticsPeriodKind.RANGE
        if not is_range and (self.first_day, self.last_day) != (None, None):
            raise DaysOutsideRangeError
        if not is_range:
            return
        if self.first_day is None or self.last_day is None:
            raise RangeDaysRequiredError
        if self.first_day > self.last_day:
            raise RangeEndingBeforeStartError

    @classmethod
    def named(cls, name: str, first_day: date | None = None, last_day: date | None = None) -> StatisticsPeriod:
        kinds = {kind.value: kind for kind in StatisticsPeriodKind}
        if name not in kinds:
            raise UnknownStatisticsPeriodError(tuple(kinds))
        return cls(kinds[name], first_day, last_day)

    def window(self, now: datetime) -> TimeWindow:
        if self.kind in LAST_DAYS:
            return TimeWindow(since=now - timedelta(days=LAST_DAYS[self.kind]))
        if self.first_day is None or self.last_day is None:
            return TimeWindow()
        return TimeWindow(since=_start_of(self.first_day), until=_start_of(self.last_day + timedelta(days=1)))


def _start_of(day: date) -> datetime:
    return datetime.combine(day, time(), tzinfo=UTC)
