from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import IntEnum

PAGE_SIZE = 50
FUNDING = "funding"


class OperationSource(IntEnum):
    """Where a row of the ledger comes from; it orders two rows of the same instant."""

    EXECUTION = 0
    FUNDING = 1


@dataclass(frozen=True, slots=True, order=True)
class OperationCursor:
    """The place of a row in the ledger, newest first: the next page starts right after it (ADR 0074)."""

    occurred_at: datetime
    source: OperationSource
    row_id: int


@dataclass(frozen=True, slots=True)
class Operation:
    """A row of the ledger as the user reads it: an execution with its kind, or a funding payment (ADR 0063).

    Sizes are signed, positive for a purchase; a funding payment has no size and no price.
    """

    cursor: OperationCursor
    asset: str
    kind: str
    size: Decimal | None
    price: Decimal | None
    fee: Decimal
    realized_pnl: Decimal
    funding: Decimal

    @property
    def occurred_at(self) -> datetime:
        return self.cursor.occurred_at


@dataclass(frozen=True, slots=True)
class OperationsQuery:
    """Which rows to read: an asset, a period from `since` included to `until` excluded, and the page after a row."""

    asset: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    after: OperationCursor | None = None
    limit: int = PAGE_SIZE

    def admits(self, operation: Operation) -> bool:
        return (
            (self.asset is None or operation.asset == self.asset)
            and (self.since is None or operation.occurred_at >= self.since)
            and (self.until is None or operation.occurred_at < self.until)
            and (self.after is None or operation.cursor < self.after)
        )


@dataclass(frozen=True, slots=True)
class OperationsPage:
    """One page of rows, newest first, and where the next page starts if there is one."""

    operations: tuple[Operation, ...]
    next: OperationCursor | None

    @classmethod
    def of(cls, newest_first: list[Operation], limit: int) -> OperationsPage:
        """The page from up to one row more than the limit: that extra row says another page follows."""
        page = tuple(newest_first[:limit])
        more = len(newest_first) > limit
        return cls(page, page[-1].cursor if more and page else None)
