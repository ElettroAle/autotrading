from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from autotrading.domain.flows.unattributable import UnattributableItem, UnattributableKind

UNATTRIBUTABLE_PAGE_SIZE = 50


@dataclass(frozen=True, slots=True, order=True)
class UnattributableCursor:
    """The place of a case in the record of an account, newest first: its instant, then its key (ADR 0074)."""

    detected_at: datetime
    item_id: UUID


@dataclass(frozen=True, slots=True)
class RecordedUnattributable:
    """A case no flow explains as the record of the account keeps it, open or resolved."""

    item_id: UUID
    item: UnattributableItem

    @property
    def cursor(self) -> UnattributableCursor:
        return UnattributableCursor(self.item.detected_at, self.item_id)


@dataclass(frozen=True, slots=True)
class UnattributableFilter:
    """What the user asks of the record of an account: a kind and a period from `since` included to `until` excluded.

    A missing value does not narrow.
    """

    kind: UnattributableKind | None = None
    since: datetime | None = None
    until: datetime | None = None
    limit: int = UNATTRIBUTABLE_PAGE_SIZE

    def admits(self, case: RecordedUnattributable, after: UnattributableCursor | None = None) -> bool:
        item = case.item
        return (
            (self.kind is None or item.kind is self.kind)
            and (self.since is None or item.detected_at >= self.since)
            and (self.until is None or item.detected_at < self.until)
            and (after is None or case.cursor < after)
        )


@dataclass(frozen=True, slots=True)
class UnattributablePage:
    """A page of the record, newest first, where the next page starts if there is one, and how many cases the filter
    admits in all with the net of their changes of the balance, whatever the page (ADR
    movimenti-non-spiegati-nel-riquadro-del-conto).
    """

    cases: tuple[RecordedUnattributable, ...]
    next: UnattributableCursor | None
    count: int
    net_change: Decimal

    @classmethod
    def of(
        cls, newest_first: Sequence[RecordedUnattributable], limit: int, count: int, net_change: Decimal
    ) -> UnattributablePage:
        """The page from up to one case more than the limit: that extra case says another page follows."""
        page = tuple(newest_first[:limit])
        more = len(newest_first) > limit
        return cls(page, page[-1].cursor if more and page else None, count, net_change)

    @staticmethod
    def net_change_of(cases: Iterable[RecordedUnattributable]) -> Decimal:
        """The sum of the changes of the balance: a position or an execution moves no balance of its own."""
        return sum(
            (case.item.amount for case in cases if case.item.kind is UnattributableKind.BALANCE_CHANGE), Decimal(0)
        )
