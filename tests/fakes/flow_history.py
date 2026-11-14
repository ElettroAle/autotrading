"""The histories of the flows in memory, filtered as the SQL adapter filters them (R2.5.1, ADR 0138)."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from autotrading.domain.flows.history import (
    ClosedPositionHistoryEntry,
    CycleHistoryEntry,
    HistoryEntry,
    HistoryQuery,
    OrderHistoryEntry,
)


@dataclass(frozen=True, slots=True)
class HistoryRow[T: HistoryEntry]:
    """A row with what the filters read of it: where it belongs, its instant, its assets and its version."""

    entry: T
    account_id: UUID
    flow_id: UUID | None
    at: datetime
    assets: frozenset[str]
    version: int | None

    def admitted_by(self, query: HistoryQuery) -> bool:
        criteria, after = query.criteria, query.after
        return (
            (criteria.flow_id is None or self.flow_id == criteria.flow_id)
            and (criteria.account_id is None or self.account_id == criteria.account_id)
            and (criteria.asset is None or criteria.asset in self.assets)
            and (criteria.version is None or self.version == criteria.version)
            and query.window.contains(self.at)
            and (after is None or self.entry.cursor < after)
        )


@dataclass
class HistoryStore:
    """The rows of one tenant: the fake is bound to the tenant of the request by the store it receives."""

    cycles: list[HistoryRow[CycleHistoryEntry]] = field(default_factory=list)
    closed_positions: list[HistoryRow[ClosedPositionHistoryEntry]] = field(default_factory=list)
    orders: list[HistoryRow[OrderHistoryEntry]] = field(default_factory=list)


class InMemoryFlowHistoryAdapter:
    def __init__(self, store: HistoryStore) -> None:
        self.store = store
        self.queries: list[HistoryQuery] = []

    def cycles(self, query: HistoryQuery) -> list[CycleHistoryEntry]:
        return self._newest(self.store.cycles, query)

    def closed_positions(self, query: HistoryQuery) -> list[ClosedPositionHistoryEntry]:
        return self._newest(self.store.closed_positions, query)

    def orders(self, query: HistoryQuery) -> list[OrderHistoryEntry]:
        return self._newest(self.store.orders, query)

    def _newest[T: HistoryEntry](self, rows: list[HistoryRow[T]], query: HistoryQuery) -> list[T]:
        self.queries.append(query)
        admitted = sorted((row.entry for row in rows if row.admitted_by(query)), key=lambda entry: entry.cursor)
        return list(reversed(admitted))[: query.limit + 1]
