from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from autotrading.adapters.outbound.sqlalchemy.reconciliation_repository import (
    _alarm_of,
    _alarm_row_of,
    _reading_of,
    _reading_row_of,
)
from autotrading.domain.flows.account_reconciliation import AccountReading
from autotrading.domain.flows.balance_comparison import BalanceComparison
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
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
