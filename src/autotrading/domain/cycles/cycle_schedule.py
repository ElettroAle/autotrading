from dataclasses import dataclass
from datetime import datetime, timedelta

from autotrading.domain.cycles.errors import InvalidScheduleError

PUNCTUALITY = timedelta(seconds=60)
# A source answers within a quarter of the interval, and never later than a minute (R1.2.5).
LONGEST_SOURCE_WAIT = timedelta(seconds=60)
SOURCE_WAIT_SHARE = 4


@dataclass(frozen=True, slots=True)
class CycleSchedule:
    """The first cycle at the start or the resume of the flow, then one every interval from there (R1.2.1)."""

    anchor: datetime
    interval: timedelta

    def __post_init__(self) -> None:
        if self.anchor.tzinfo is None or self.interval <= timedelta(0):
            raise InvalidScheduleError

    @classmethod
    def planned(cls, runs_cycles: bool, anchor: datetime | None, interval: timedelta) -> CycleSchedule | None:
        """Only a running flow stamped with its anchor has cycles planned (R1.7.3)."""
        if not runs_cycles or anchor is None:
            return None
        return cls(anchor, interval)

    def due_at(self, now: datetime) -> datetime | None:
        """The latest planned instant not after now; None before the first one."""
        if now < self.anchor:
            return None
        return self.anchor + (now - self.anchor) // self.interval * self.interval

    def next_after(self, now: datetime) -> datetime:
        """The first planned instant strictly after now."""
        if now < self.anchor:
            return self.anchor
        return self.anchor + ((now - self.anchor) // self.interval + 1) * self.interval

    @property
    def source_wait(self) -> timedelta:
        return min(self.interval / SOURCE_WAIT_SHARE, LONGEST_SOURCE_WAIT)


def delay_seconds(planned_at: datetime, started_at: datetime) -> int | None:
    """The delay of a late cycle in whole seconds; a cycle started within a minute of its instant is punctual."""
    delay = started_at - planned_at
    if delay <= PUNCTUALITY:
        return None
    return int(delay.total_seconds())
