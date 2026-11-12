from dataclasses import dataclass

from autotrading.domain.cycles.cycle_record import CycleRecord
from autotrading.domain.cycles.errors import InvalidPageNumberError

CYCLES_PER_PAGE = 50


@dataclass(frozen=True, slots=True)
class PageNumber:
    """A page of the cycles of a flow, from the most recent; the first page is 1 (R1.7.3)."""

    value: int

    def __post_init__(self) -> None:
        if self.value < 1:
            raise InvalidPageNumberError

    @property
    def offset(self) -> int:
        return (self.value - 1) * CYCLES_PER_PAGE


@dataclass(frozen=True, slots=True)
class CyclePage:
    number: int
    cycles: tuple[CycleRecord, ...]
    has_next: bool
