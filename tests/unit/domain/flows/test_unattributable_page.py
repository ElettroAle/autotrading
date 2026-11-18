"""The record of what no flow explains on an account, newest first, by pages of keyset with the net of the changes of
the balance the filter admits (ADR movimenti-non-spiegati-nel-riquadro-del-conto, ADR 0074).
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.domain.flows.unattributable import UnattributableItem, UnattributableKind
from autotrading.domain.flows.unattributable_page import (
    UNATTRIBUTABLE_PAGE_SIZE,
    RecordedUnattributable,
    UnattributableCursor,
    UnattributableFilter,
    UnattributablePage,
)

ACCOUNT = uuid4()
NOON = datetime(2026, 11, 17, 12, tzinfo=UTC)


def a_case(
    kind: UnattributableKind = UnattributableKind.BALANCE_CHANGE,
    at: datetime = NOON,
    amount: str = "-0.03",
    item_id: UUID | None = None,
) -> RecordedUnattributable:
    item = UnattributableItem(ACCOUNT, kind, "ref", None, Decimal(amount), at)
    return RecordedUnattributable(item_id or uuid4(), item)


def test_the_page_has_fifty_cases() -> None:
    assert UNATTRIBUTABLE_PAGE_SIZE == 50
    assert UnattributableFilter().limit == UNATTRIBUTABLE_PAGE_SIZE


def test_a_case_is_found_again_by_its_instant_then_its_key() -> None:
    case = a_case()

    assert case.cursor == UnattributableCursor(NOON, case.item_id)


def test_the_cursors_order_by_instant_then_by_key() -> None:
    low, high = sorted((uuid4(), uuid4()))

    assert UnattributableCursor(NOON, high) > UnattributableCursor(NOON, low)
    assert UnattributableCursor(NOON + timedelta(seconds=1), low) > UnattributableCursor(NOON, high)


def test_a_filter_without_values_admits_every_case() -> None:
    assert UnattributableFilter().admits(a_case())


@pytest.mark.parametrize(
    ("narrowed", "admitted"),
    [
        (UnattributableFilter(kind=UnattributableKind.BALANCE_CHANGE), True),
        (UnattributableFilter(kind=UnattributableKind.POSITION), False),
        (UnattributableFilter(since=NOON), True),
        (UnattributableFilter(since=NOON + timedelta(seconds=1)), False),
        (UnattributableFilter(until=NOON + timedelta(seconds=1)), True),
        (UnattributableFilter(until=NOON), False),
    ],
)
def test_a_filter_narrows_by_kind_and_by_period_from_since_included_to_until_excluded(
    narrowed: UnattributableFilter, admitted: bool
) -> None:
    assert narrowed.admits(a_case()) is admitted


def test_the_page_after_a_case_admits_only_the_older_ones() -> None:
    case = a_case()
    older = a_case(at=NOON - timedelta(minutes=1))

    assert not UnattributableFilter().admits(case, after=case.cursor)
    assert UnattributableFilter().admits(older, after=case.cursor)


def test_the_net_of_the_changes_sums_only_the_changes_of_the_balance() -> None:
    cases = [
        a_case(amount="-0.03"),
        a_case(amount="0.05"),
        a_case(UnattributableKind.POSITION, amount="0.1"),
    ]

    assert UnattributablePage.net_change_of(cases) == Decimal("0.02")


def test_a_page_with_one_case_more_than_the_limit_says_where_the_next_starts() -> None:
    cases = [a_case(at=NOON - timedelta(minutes=minute)) for minute in range(3)]

    page = UnattributablePage.of(cases, 2, count=3, net_change=Decimal(1))

    assert page.cases == tuple(cases[:2])
    assert page.next == cases[1].cursor
    assert (page.count, page.net_change) == (3, Decimal(1))


def test_the_last_page_has_no_next() -> None:
    cases = [a_case()]

    page = UnattributablePage.of(cases, 2, count=1, net_change=Decimal(0))

    assert page.next is None
