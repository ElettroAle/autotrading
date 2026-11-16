from dataclasses import dataclass

from autotrading.domain.flows.cycle_record import CycleRecord

CYCLES_PER_PAGE = 50


@dataclass(frozen=True, slots=True)
class CyclePage:
    """A page of the cycles of a flow that match a filter, from the most recent, and how many match in all."""

    number: int
    cycles: tuple[CycleRecord, ...]
    has_next: bool
    total: int
