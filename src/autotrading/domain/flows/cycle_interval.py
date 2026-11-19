from dataclasses import dataclass
from datetime import timedelta

from autotrading.domain.flows.cycle_schedule import source_wait_of
from autotrading.domain.flows.errors import CycleIntervalOutOfRangeError

MINIMUM_MINUTES = 1
MAXIMUM_MINUTES = 1440
DEFAULT_MINUTES = 15


@dataclass(frozen=True, slots=True)
class CycleInterval:
    """Whole minutes between two cycles, from one minute to one day (R1.1.1)."""

    minutes: int

    def __post_init__(self) -> None:
        if not MINIMUM_MINUTES <= self.minutes <= MAXIMUM_MINUTES:
            raise CycleIntervalOutOfRangeError

    @classmethod
    def of(cls, minutes: int | None) -> CycleInterval:
        return DEFAULT_CYCLE_INTERVAL if minutes is None else cls(minutes)

    @property
    def source_wait(self) -> timedelta:
        """How long a cycle of this interval waits for a source (R1.2.5)."""
        return source_wait_of(timedelta(minutes=self.minutes))


# The interval of a flow that names none: a trial of a source reads it as a cycle of this interval (R6.3.1).
DEFAULT_CYCLE_INTERVAL = CycleInterval(DEFAULT_MINUTES)
