from dataclasses import dataclass

from autotrading.domain.flows.cycle_record import CycleRecord

CYCLES_PER_PAGE = 50


@dataclass(frozen=True, slots=True)
class CyclePage:
    number: int
    cycles: tuple[CycleRecord, ...]
    has_next: bool
