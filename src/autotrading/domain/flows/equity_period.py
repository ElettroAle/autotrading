from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from autotrading.domain.flows.errors import EquityRangeIncompleteError, EquityRangeInvertedError


@dataclass(frozen=True, slots=True)
class EquityWindow:
    """The instants of a period, from `since` included to `until` excluded; a missing bound leaves that side open."""

    since: datetime | None
    until: datetime | None

    def admits(self, instant: datetime) -> bool:
        return (self.since is None or instant >= self.since) and (self.until is None or instant < self.until)


class EquityPeriod(StrEnum):
    """The periods of the equity curve the user chooses from; the whole life of the flow is the default (R2.2.3)."""

    LIFETIME = "lifetime"
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"
    RANGE = "range"

    def window(self, now: datetime, start: datetime | None = None, end: datetime | None = None) -> EquityWindow:
        """The instants of the period: the last days end now, a range is the one the user gives."""
        if self is EquityPeriod.LIFETIME:
            return EquityWindow(None, None)
        if self is EquityPeriod.LAST_7_DAYS:
            return EquityWindow(now - timedelta(days=7), None)
        if self is EquityPeriod.LAST_30_DAYS:
            return EquityWindow(now - timedelta(days=30), None)
        return _range(start, end)


def _range(start: datetime | None, end: datetime | None) -> EquityWindow:
    if start is None or end is None:
        raise EquityRangeIncompleteError
    if start >= end:
        raise EquityRangeInvertedError
    return EquityWindow(start, end)
