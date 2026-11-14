from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from autotrading.application.flows.ports import HistoricalOrdersPort
from autotrading.domain.flows.history import HistoryCursor, HistoryFilter, HistoryPage, HistoryQuery, OrderHistoryEntry


@dataclass(frozen=True, slots=True)
class QueryOrderHistoryCommand:
    criteria: HistoryFilter
    after: HistoryCursor | None = None


class QueryOrderHistoryUseCase:
    """The orders sent on the accounts of the tenant that match the filter, each with its executions, from the most
    recent, in pages of 50 (R2.5.1).
    """

    def __init__(self, orders: HistoricalOrdersPort, clock: Callable[[], datetime]) -> None:
        self._orders = orders
        self._clock = clock

    def execute(self, command: QueryOrderHistoryCommand) -> HistoryPage[OrderHistoryEntry]:
        query = HistoryQuery.of(command.criteria, self._clock(), command.after)
        return HistoryPage.of(self._orders.orders(query), query.limit)
