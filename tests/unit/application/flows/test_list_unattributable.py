"""The record of what no flow explains on an account of the tenant, newest first, by pages, with the net of the changes
of the balance of the filter (R1.6.2, R3.3.2, ADR movimenti-non-spiegati-nel-riquadro-del-conto).
"""

from datetime import timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.flows.errors import FlowAccountNotFoundError
from autotrading.application.flows.list_unattributable import ListUnattributableCommand, ListUnattributableUseCase
from autotrading.domain.flows.unattributable import UnattributableItem, UnattributableKind
from autotrading.domain.flows.unattributable_page import UnattributableFilter
from tests.fakes.account_thresholds import FakeAccountThresholdsAdapter
from tests.fakes.reconciliation_repository import InMemoryReconciliationRepositoryAdapter
from tests.support.activity import READ_AT

ACCOUNT, OTHER = uuid4(), uuid4()


def a_change(account_id: UUID, minutes: int, amount: str) -> UnattributableItem:
    return UnattributableItem(
        account_id,
        UnattributableKind.BALANCE_CHANGE,
        f"change-{minutes}",
        None,
        Decimal(amount),
        READ_AT + timedelta(minutes=minutes),
    )


def a_position(account_id: UUID, minutes: int, asset: str) -> UnattributableItem:
    return UnattributableItem(
        account_id, UnattributableKind.POSITION, asset, asset, Decimal("0.1"), READ_AT + timedelta(minutes=minutes)
    )


def use_case_on(readings: InMemoryReconciliationRepositoryAdapter) -> ListUnattributableUseCase:
    return ListUnattributableUseCase(readings, FakeAccountThresholdsAdapter({ACCOUNT: "test-1"}))


def test_the_cases_of_the_account_come_from_the_most_recent_with_the_net_of_the_changes() -> None:
    readings = InMemoryReconciliationRepositoryAdapter()
    for item in (
        a_change(ACCOUNT, 0, "-0.03"),
        a_position(ACCOUNT, 1, "SOL"),
        a_change(OTHER, 2, "9"),
        a_change(ACCOUNT, 3, "0.05"),
    ):
        readings.record(item)

    page = use_case_on(readings).execute(ListUnattributableCommand(ACCOUNT, UnattributableFilter()))

    assert [case.item.reference for case in page.cases] == ["change-3", "SOL", "change-0"]
    assert (page.count, page.net_change, page.next) == (3, Decimal("0.02"), None)


def test_a_resolved_position_stays_in_the_record() -> None:
    readings = InMemoryReconciliationRepositoryAdapter()
    readings.record(a_position(ACCOUNT, 0, "SOL"))
    readings.resolve_positions(ACCOUNT, frozenset())

    page = use_case_on(readings).execute(ListUnattributableCommand(ACCOUNT, UnattributableFilter()))

    assert [case.item.asset for case in page.cases] == ["SOL"]


def test_the_next_page_starts_after_the_last_case_and_the_totals_cover_the_whole_filter() -> None:
    readings = InMemoryReconciliationRepositoryAdapter()
    for minute in range(3):
        readings.record(a_change(ACCOUNT, minute, "1"))
    criteria = UnattributableFilter(kind=UnattributableKind.BALANCE_CHANGE, limit=2)
    use_case = use_case_on(readings)

    first = use_case.execute(ListUnattributableCommand(ACCOUNT, criteria))
    second = use_case.execute(ListUnattributableCommand(ACCOUNT, criteria, first.next))

    assert [case.item.reference for case in first.cases] == ["change-2", "change-1"]
    assert [case.item.reference for case in second.cases] == ["change-0"]
    assert (second.count, second.net_change, second.next) == (3, Decimal(3), None)


def test_an_account_the_tenant_does_not_have_is_not_found() -> None:
    with pytest.raises(FlowAccountNotFoundError):
        use_case_on(InMemoryReconciliationRepositoryAdapter()).execute(
            ListUnattributableCommand(OTHER, UnattributableFilter())
        )
