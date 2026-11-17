from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from autotrading.application.flows.ports import HistoricalClosedPositionsPort
from autotrading.domain.flows.history import (
    ClosedPositionHistoryEntry,
    ClosedPositionHistoryTotals,
    HistoryCursor,
    HistoryFilter,
    HistoryPage,
    HistoryQuery,
    HistoryReport,
)


@dataclass(frozen=True, slots=True)
class QueryClosedPositionHistoryCommand:
    criteria: HistoryFilter
    after: HistoryCursor | None = None


class QueryClosedPositionHistoryUseCase:
    """The closed positions of the flows of the tenant that match the filter, from the most recent close, in pages of
    50 (R2.5.1); the first page with the PnL and the fees of all of them (Bug 569).
    """

    def __init__(self, positions: HistoricalClosedPositionsPort, clock: Callable[[], datetime]) -> None:
        self._positions = positions
        self._clock = clock

    def execute(
        self, command: QueryClosedPositionHistoryCommand
    ) -> HistoryReport[ClosedPositionHistoryEntry, ClosedPositionHistoryTotals]:
        query = HistoryQuery.of(command.criteria, self._clock(), command.after)
        page = HistoryPage.of(self._positions.closed_positions(query), query.limit)
        return HistoryReport(page, self._totals_of(query))

    def _totals_of(self, query: HistoryQuery) -> ClosedPositionHistoryTotals | None:
        if not query.first_page:
            return None
        return self._positions.closed_position_totals(query)
