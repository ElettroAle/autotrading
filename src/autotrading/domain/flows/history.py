from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from autotrading.domain.flows.closed_position import ClosedPosition
from autotrading.domain.flows.cycle_record import CycleRecord
from autotrading.domain.flows.errors import VersionWithoutFlowError
from autotrading.domain.flows.statistics_period import StatisticsPeriod, StatisticsPeriodKind, TimeWindow

HISTORY_PAGE_SIZE = 50


@dataclass(frozen=True, slots=True)
class HistoryFilter:
    """What the user asks of a history: flow, account, period, asset and configuration version, in any combination
    (R2.5.1). A missing value does not narrow; a version is numbered within its flow, so it needs the flow.
    """

    flow_id: UUID | None = None
    account_id: UUID | None = None
    period: StatisticsPeriod = field(default_factory=lambda: StatisticsPeriod(StatisticsPeriodKind.ALL))
    asset: str | None = None
    version: int | None = None

    def __post_init__(self) -> None:
        if self.version is not None and self.flow_id is None:
            raise VersionWithoutFlowError


@dataclass(frozen=True, slots=True, order=True)
class HistoryCursor:
    """The place of a row in a history, newest first: its instant, then its key (ADR 0138)."""

    at: datetime
    key: UUID


@dataclass(frozen=True, slots=True)
class HistoryQuery:
    """A filter read at an instant, so its period becomes a window, and the page after a row."""

    criteria: HistoryFilter
    window: TimeWindow
    after: HistoryCursor | None = None
    limit: int = HISTORY_PAGE_SIZE

    @classmethod
    def of(cls, criteria: HistoryFilter, now: datetime, after: HistoryCursor | None) -> HistoryQuery:
        return cls(criteria, criteria.period.window(now), after)


@dataclass(frozen=True, slots=True)
class CycleHistoryEntry:
    """A cycle in the history, with the name of its flow and the configuration version in force when it ran."""

    flow_name: str
    version: int | None
    record: CycleRecord

    @property
    def cursor(self) -> HistoryCursor:
        return HistoryCursor(self.record.planned_at, self.record.flow_id)


@dataclass(frozen=True, slots=True)
class ClosedPositionHistoryEntry:
    """A closed position in the history, with the name of its flow."""

    position_id: UUID
    flow_name: str
    position: ClosedPosition

    @property
    def cursor(self) -> HistoryCursor:
        return HistoryCursor(self.position.closing.at, self.position_id)


@dataclass(frozen=True, slots=True)
class OrderExecution:
    """An execution of an order, as the exchange reported it: the size is signed, positive for a purchase."""

    executed_at: datetime
    price: Decimal
    size: Decimal
    fee: Decimal


@dataclass(frozen=True, slots=True)
class OrderHistoryEntry:
    """An order the platform sent, with its outcome and its executions; an order of no flow has no flow name."""

    order_id: UUID
    created_at: datetime
    account_id: UUID
    account_name: str
    flow_id: UUID | None
    flow_name: str | None
    asset: str
    direction: str
    closing: bool
    leverage: int
    requested_size: Decimal
    status: str
    origin: str
    executions: tuple[OrderExecution, ...]

    @property
    def cursor(self) -> HistoryCursor:
        return HistoryCursor(self.created_at, self.order_id)


type HistoryEntry = CycleHistoryEntry | ClosedPositionHistoryEntry | OrderHistoryEntry


@dataclass(frozen=True, slots=True)
class HistoryPage[T: HistoryEntry]:
    """One page of a history, newest first, and where the next page starts if there is one."""

    entries: tuple[T, ...]
    next: HistoryCursor | None

    @classmethod
    def of(cls, newest_first: Sequence[T], limit: int) -> HistoryPage[T]:
        """The page from up to one row more than the limit: that extra row says another page follows."""
        page = tuple(newest_first[:limit])
        more = len(newest_first) > limit
        return cls(page, page[-1].cursor if more and page else None)
