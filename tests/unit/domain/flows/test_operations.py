from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from autotrading.domain.flows.operations import (
    FUNDING,
    PAGE_SIZE,
    Operation,
    OperationCursor,
    OperationSource,
    OperationsPage,
    OperationsQuery,
)

NOON = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)


def an_operation(
    minutes: int = 0, *, asset: str = "BTC", source: OperationSource = OperationSource.EXECUTION, row_id: int = 1
) -> Operation:
    cursor = OperationCursor(NOON + timedelta(minutes=minutes), source, row_id)
    return Operation(cursor, asset, "ordine_flusso", Decimal(1), Decimal(100), Decimal(0), Decimal(0), Decimal(0))


def test_a_page_holds_fifty_operations_by_default() -> None:
    assert PAGE_SIZE == 50
    assert OperationsQuery().limit == PAGE_SIZE


def test_the_cursor_orders_by_instant_then_source_then_row() -> None:
    execution = OperationCursor(NOON, OperationSource.EXECUTION, 9)
    funding = OperationCursor(NOON, OperationSource.FUNDING, 1)
    later = OperationCursor(NOON + timedelta(seconds=1), OperationSource.EXECUTION, 1)

    assert execution < funding < later
    assert OperationCursor(NOON, OperationSource.EXECUTION, 1) < execution


def test_an_operation_happens_at_the_instant_of_its_cursor() -> None:
    assert an_operation(5).occurred_at == NOON + timedelta(minutes=5)


def test_a_query_without_filters_admits_every_operation() -> None:
    assert OperationsQuery().admits(an_operation())


@pytest.mark.parametrize(
    ("query", "admitted"),
    [
        (OperationsQuery(asset="BTC"), True),
        (OperationsQuery(asset="ETH"), False),
        (OperationsQuery(since=NOON), True),
        (OperationsQuery(since=NOON + timedelta(seconds=1)), False),
        (OperationsQuery(until=NOON + timedelta(seconds=1)), True),
        (OperationsQuery(until=NOON), False),
        (OperationsQuery(after=OperationCursor(NOON, OperationSource.EXECUTION, 2)), True),
        (OperationsQuery(after=OperationCursor(NOON, OperationSource.EXECUTION, 1)), False),
    ],
)
def test_a_query_admits_the_asset_the_period_from_since_to_until_and_the_rows_after_the_cursor(
    query: OperationsQuery, admitted: bool
) -> None:
    assert query.admits(an_operation()) is admitted


def test_a_page_with_one_row_more_than_the_limit_says_where_the_next_starts() -> None:
    rows = [an_operation(-minute, row_id=minute) for minute in range(4)]

    page = OperationsPage.of(rows, 3)

    assert page.operations == tuple(rows[:3])
    assert page.next == rows[2].cursor


def test_the_last_page_has_no_next() -> None:
    rows = [an_operation(-minute, row_id=minute) for minute in range(3)]

    assert OperationsPage.of(rows, 3) == OperationsPage(tuple(rows), None)


def test_an_empty_page_has_no_next() -> None:
    assert OperationsPage.of([], 3) == OperationsPage((), None)


def test_a_funding_payment_is_named_funding() -> None:
    assert FUNDING == "funding"
