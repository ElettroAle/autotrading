from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from autotrading.domain.flows.capital_change import CapitalChange, CapitalChangeReason
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.page_number import PageNumber

CAPITAL_CHANGES_PER_PAGE = 50


class TransferDirection(StrEnum):
    """Which way a movement the exchange declares on an account took the money (R3.4.2)."""

    DEPOSIT = "deposito"
    WITHDRAWAL = "prelievo"


type EntryReason = CapitalChangeReason | TransferDirection


@dataclass(frozen=True, slots=True)
class AccountTransfer:
    """A deposit or a withdrawal the exchange declares on an account, at the instant it declares; the amount is always
    positive, the direction says which way it went (R3.4.2)."""

    transferred_at: datetime
    amount: Decimal
    direction: TransferDirection


@dataclass(frozen=True, slots=True)
class CapitalHistoryEntry:
    """A row of the history of the capital: a change of a flow, with its capital before and after, or a deposit or a
    withdrawal of the account, which belongs to no flow (R3.4.2)."""

    occurred_at: datetime
    reason: EntryReason
    amount: Decimal
    flow_id: FlowId | None = None
    flow_name: str | None = None
    previous: Decimal | None = None
    new: Decimal | None = None

    @classmethod
    def of_change(cls, change: CapitalChange, flow_name: str) -> CapitalHistoryEntry:
        return cls(
            change.changed_at, change.reason, change.amount, change.flow_id, flow_name, change.previous, change.new
        )

    @classmethod
    def of_transfer(cls, transfer: AccountTransfer) -> CapitalHistoryEntry:
        return cls(transfer.transferred_at, transfer.direction, transfer.amount)


@dataclass(frozen=True, slots=True)
class CapitalHistoryPage:
    """A page of the history of the capital, from the most recent row, how many rows the period holds in all and the
    currency of the amounts."""

    number: int
    entries: tuple[CapitalHistoryEntry, ...]
    has_next: bool
    total: int
    currency: str

    @classmethod
    def of(
        cls, number: PageNumber, entries: Iterable[CapitalHistoryEntry], total: int, currency: str
    ) -> CapitalHistoryPage:
        """The page among the newest rows of every source, put together newest first; rows of the same instant keep
        the order given."""
        ordered = sorted(entries, key=lambda entry: entry.occurred_at, reverse=True)
        start = number.offset(CAPITAL_CHANGES_PER_PAGE)
        end = start + CAPITAL_CHANGES_PER_PAGE
        return cls(number.value, tuple(ordered[start:end]), len(ordered) > end, total, currency)


def entries_to_read(number: PageNumber) -> int:
    """How many of the newest rows of each source the page needs: those of the pages before, its own, and one more
    that tells whether another page follows."""
    return number.offset(CAPITAL_CHANGES_PER_PAGE) + CAPITAL_CHANGES_PER_PAGE + 1
