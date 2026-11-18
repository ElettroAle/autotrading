from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.sql import ClauseElement

from autotrading.adapters.outbound.sqlalchemy.reconciliation_repository import (
    _admitted,
    _after,
    _alarm_of,
    _alarm_row_of,
    _reading_of,
    _reading_row_of,
    _recorded_of,
    _row_of,
    _totals,
)
from autotrading.domain.flows.account_reconciliation import AccountReading
from autotrading.domain.flows.balance_comparison import BalanceComparison
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
from autotrading.domain.flows.unattributable import UnattributableItem, UnattributableKind
from autotrading.domain.flows.unattributable_page import UnattributableCursor, UnattributableFilter
from autotrading.domain.tenancy.tenant_id import TenantId

READ_AT = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
TENANT = TenantId.new()
ACCOUNT = uuid4()


def test_a_reading_with_its_comparison_is_read_back_as_saved() -> None:
    flow_id = FlowId.new()
    comparison = BalanceComparison(Decimal(1000), Decimal(980), READ_AT)
    reading = AccountReading(ACCOUNT, READ_AT, {flow_id: frozenset({"BTC"})}, Decimal(1000), comparison)

    row = _reading_row_of(reading, TENANT)

    assert (row["reference_balance"], row["expected_balance"], row["read_balance"]) == (
        Decimal(1000),
        Decimal(1000),
        Decimal(980),
    )
    assert _reading_of(row) == reading  # type: ignore[arg-type]  # a dict stands for the row mapping of a query


def test_a_reading_saved_before_the_balances_were_compared_has_neither_reference_nor_comparison() -> None:
    reading = AccountReading(ACCOUNT, READ_AT, {})

    row = _reading_row_of(reading, TENANT)

    assert (row["reference_balance"], row["expected_balance"], row["read_balance"]) == (None, None, None)
    assert _reading_of(row) == reading  # type: ignore[arg-type]  # a dict stands for the row mapping of a query


def test_an_alarm_is_read_back_as_saved() -> None:
    alarm = ReconciliationAlarm(ACCOUNT, Decimal(1000), Decimal(980), Decimal(2), READ_AT, READ_AT + timedelta(hours=1))

    row = _alarm_row_of(alarm, TENANT)

    assert row["tenant_id"] == TENANT.value
    assert _alarm_of(row) == alarm  # type: ignore[arg-type]  # a dict stands for the row mapping of a query


# The record of the account (ADR movimenti-non-spiegati-nel-riquadro-del-conto)


def sql_of(clause: ClauseElement) -> str:
    return str(clause.compile())


def test_a_recorded_case_is_read_back_with_its_key() -> None:
    item = UnattributableItem(ACCOUNT, UnattributableKind.BALANCE_CHANGE, "ref", None, Decimal("-0.03"), READ_AT)
    row = _row_of(item, TENANT)

    recorded = _recorded_of(row)  # type: ignore[arg-type]  # a dict stands for the row mapping of a query

    assert (recorded.item_id, recorded.item) == (row["id"], item)


def test_a_filter_without_values_narrows_only_to_the_account() -> None:
    assert [sql_of(clause) for clause in _admitted(ACCOUNT, UnattributableFilter())] == [
        "unattributable_items.account_id = :account_id_1"
    ]


def params_of(clause: ClauseElement) -> dict[str, object]:
    return dict(clause.compile().params)


def test_a_filter_narrows_by_kind_and_by_period() -> None:
    until = READ_AT + timedelta(hours=1)
    criteria = UnattributableFilter(UnattributableKind.POSITION, READ_AT, until)

    _, kind, since, before = _admitted(ACCOUNT, criteria)

    assert ("kind =" in sql_of(kind), list(params_of(kind).values())) == (True, ["position"])
    assert (">=" in sql_of(since), list(params_of(since).values())) == (True, [READ_AT])
    assert ("detected_at <" in sql_of(before), list(params_of(before).values())) == (True, [until])


def test_the_first_page_starts_from_the_newest_and_the_next_after_its_cursor() -> None:
    assert _after(None) == []
    [after] = _after(UnattributableCursor(READ_AT, uuid4()))
    assert "(unattributable_items.detected_at, unattributable_items.id) <" in sql_of(after)


def test_the_totals_count_every_case_and_sum_only_the_changes_of_the_balance() -> None:
    sql = sql_of(_totals(_admitted(ACCOUNT, UnattributableFilter())))

    assert "count(*) AS count" in sql
    assert "THEN unattributable_items.amount" in sql
    assert params_of(_totals([]))["kind_1"] == "balance_change"
