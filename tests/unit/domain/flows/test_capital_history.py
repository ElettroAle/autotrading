from datetime import UTC, datetime, timedelta
from decimal import Decimal

from autotrading.domain.flows.capital_change import CapitalChange, CapitalChangeReason
from autotrading.domain.flows.capital_history import (
    CAPITAL_CHANGES_PER_PAGE,
    AccountTransfer,
    CapitalHistoryEntry,
    CapitalHistoryPage,
    EntryReason,
    TransferDirection,
    entries_to_read,
)
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.page_number import PageNumber
from autotrading.domain.tenancy.user_id import UserId

AT = datetime(2026, 11, 15, 10, tzinfo=UTC)


def an_entry(minutes: int, reason: EntryReason = TransferDirection.DEPOSIT) -> CapitalHistoryEntry:
    return CapitalHistoryEntry(AT + timedelta(minutes=minutes), reason, Decimal(minutes))


def test_a_change_of_a_flow_is_an_entry_with_the_flow_and_the_capital_before_and_after() -> None:
    flow_id = FlowId.new()
    change = CapitalChange(
        flow_id, AT, Decimal(500), Decimal(700), UserId("anna"), CapitalChangeReason.INCREASE, Decimal(200)
    )

    entry = CapitalHistoryEntry.of_change(change, "alfa")

    assert entry == CapitalHistoryEntry(
        AT, CapitalChangeReason.INCREASE, Decimal(200), flow_id, "alfa", Decimal(500), Decimal(700)
    )


def test_a_transfer_of_the_account_is_an_entry_without_flow_nor_capital() -> None:
    entry = CapitalHistoryEntry.of_transfer(AccountTransfer(AT, Decimal(300), TransferDirection.WITHDRAWAL))

    assert entry == CapitalHistoryEntry(AT, TransferDirection.WITHDRAWAL, Decimal(300))
    assert (entry.flow_id, entry.flow_name, entry.previous, entry.new) == (None, None, None, None)


def test_the_first_page_reads_one_entry_more_than_a_page() -> None:
    assert entries_to_read(PageNumber(1)) == CAPITAL_CHANGES_PER_PAGE + 1


def test_a_later_page_reads_every_entry_before_it_too() -> None:
    assert entries_to_read(PageNumber(3)) == 3 * CAPITAL_CHANGES_PER_PAGE + 1


def test_a_page_puts_the_entries_of_every_source_newest_first() -> None:
    oldest, newest, middle = an_entry(1), an_entry(3), an_entry(2, CapitalChangeReason.REDUCTION)

    page = CapitalHistoryPage.of(PageNumber(1), (oldest, newest, middle), 3, "USDC")

    assert page == CapitalHistoryPage(1, (newest, middle, oldest), False, 3, "USDC")


def test_entries_of_the_same_instant_keep_the_order_given() -> None:
    first, second = an_entry(1, CapitalChangeReason.INCREASE), an_entry(1, TransferDirection.DEPOSIT)

    assert CapitalHistoryPage.of(PageNumber(1), (first, second), 2, "USDC").entries == (first, second)


def test_a_page_says_another_follows_when_an_entry_is_left_after_it() -> None:
    entries = [an_entry(minutes) for minutes in range(CAPITAL_CHANGES_PER_PAGE + 1)]

    page = CapitalHistoryPage.of(PageNumber(1), entries, 70, "USDC")

    assert page.has_next
    assert len(page.entries) == CAPITAL_CHANGES_PER_PAGE
    assert page.entries[0] == entries[-1]
    assert page.total == 70


def test_a_later_page_skips_the_entries_of_the_pages_before() -> None:
    entries = [an_entry(minutes) for minutes in range(CAPITAL_CHANGES_PER_PAGE + 2)]

    page = CapitalHistoryPage.of(PageNumber(2), entries, len(entries), "USDC")

    assert page == CapitalHistoryPage(2, (entries[1], entries[0]), False, len(entries), "USDC")
