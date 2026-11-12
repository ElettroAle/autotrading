from dataclasses import dataclass

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
        return cls(DEFAULT_MINUTES if minutes is None else minutes)
