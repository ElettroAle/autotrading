from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from autotrading.application.flows.ports import HistoricalOrdersPort
from autotrading.domain.flows.history import (
    HistoryCursor,
    HistoryFilter,
    HistoryPage,
    HistoryQuery,
    HistoryReport,
    OrderHistoryEntry,
    OrderHistoryTotals,
)


@dataclass(frozen=True, slots=True)
class QueryOrderHistoryCommand:
    criteria: HistoryFilter
    after: HistoryCursor | None = None


class QueryOrderHistoryUseCase:
    """The orders sent on the accounts of the tenant that match the filter, each with its executions, from the most
    recent, in pages of 50 (R2.5.1); the first page with the fees of all of them (Bug 569).
    """

    def __init__(self, orders: HistoricalOrdersPort, clock: Callable[[], datetime]) -> None:
        self._orders = orders
        self._clock = clock

    def execute(self, command: QueryOrderHistoryCommand) -> HistoryReport[OrderHistoryEntry, OrderHistoryTotals]:
        query = HistoryQuery.of(command.criteria, self._clock(), command.after)
        page = HistoryPage.of(self._orders.orders(query), query.limit)
        return HistoryReport(page, self._totals_of(query))

    def _totals_of(self, query: HistoryQuery) -> OrderHistoryTotals | None:
        if not query.first_page:
            return None
        return self._orders.order_totals(query)
