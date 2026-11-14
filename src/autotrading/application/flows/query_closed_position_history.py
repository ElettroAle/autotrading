from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from autotrading.application.flows.ports import HistoricalClosedPositionsPort
from autotrading.domain.flows.history import (
    ClosedPositionHistoryEntry,
    HistoryCursor,
    HistoryFilter,
    HistoryPage,
    HistoryQuery,
)


@dataclass(frozen=True, slots=True)
class QueryClosedPositionHistoryCommand:
    criteria: HistoryFilter
    after: HistoryCursor | None = None


class QueryClosedPositionHistoryUseCase:
    """The closed positions of the flows of the tenant that match the filter, from the most recent close, in pages of
    50 (R2.5.1).
    """

    def __init__(self, positions: HistoricalClosedPositionsPort, clock: Callable[[], datetime]) -> None:
        self._positions = positions
        self._clock = clock

    def execute(self, command: QueryClosedPositionHistoryCommand) -> HistoryPage[ClosedPositionHistoryEntry]:
        query = HistoryQuery.of(command.criteria, self._clock(), command.after)
        return HistoryPage.of(self._positions.closed_positions(query), query.limit)
