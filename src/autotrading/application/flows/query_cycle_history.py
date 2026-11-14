from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from autotrading.application.flows.ports import HistoricalCyclesPort
from autotrading.domain.flows.history import CycleHistoryEntry, HistoryCursor, HistoryFilter, HistoryPage, HistoryQuery


@dataclass(frozen=True, slots=True)
class QueryCycleHistoryCommand:
    criteria: HistoryFilter
    after: HistoryCursor | None = None


class QueryCycleHistoryUseCase:
    """The cycles of the flows of the tenant that match the filter, from the most recent, in pages of 50 (R2.5.1)."""

    def __init__(self, cycles: HistoricalCyclesPort, clock: Callable[[], datetime]) -> None:
        self._cycles = cycles
        self._clock = clock

    def execute(self, command: QueryCycleHistoryCommand) -> HistoryPage[CycleHistoryEntry]:
        query = HistoryQuery.of(command.criteria, self._clock(), command.after)
        return HistoryPage.of(self._cycles.cycles(query), query.limit)
