from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.sql import ClauseElement

from autotrading.adapters.outbound.sqlalchemy.alert_repository import _admitted, _after, _alert_of, _row_of
from autotrading.domain.notifications.alert import (
    Alert,
    AlertCause,
    AlertId,
    AlertResourceKind,
    AlertSeverity,
    AlertState,
)
from autotrading.domain.notifications.alert_page import AlertCursor, AlertFilter
from autotrading.domain.notifications.notification import Amount
from autotrading.domain.tenancy.tenant_id import TenantId

OPENED_AT = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)
TENANT = TenantId.new()
ACCOUNT = uuid4()


def sql_of(clause: ClauseElement) -> str:
    return str(clause.compile())


def params_of(clause: ClauseElement) -> list[object]:
    return list(clause.compile().params.values())


def test_an_alert_is_read_back_with_its_cause_and_its_instants() -> None:
    usdc = Amount(Decimal(980), "USDC")
    cause = AlertCause.reconciliation_alarm(ACCOUNT, "test-1", usdc, usdc)
    row = {**_row_of(cause, TENANT), "opened_at": OPENED_AT, "resolved_at": OPENED_AT + timedelta(hours=1)}

    alert = _alert_of(row)  # type: ignore[arg-type]  # a dict stands for the row mapping of a query

    assert row["tenant_id"] == TENANT.value
    assert row["cause_key"] == cause.key
    assert alert == Alert(AlertId(row["id"]), cause, OPENED_AT, OPENED_AT + timedelta(hours=1))  # type: ignore[arg-type]  # the id of the row is a UUID


def test_the_asset_of_a_case_is_kept_with_its_cause() -> None:
    cause = AlertCause.unattributable_position(ACCOUNT, "test-1", "SOL")
    row = {**_row_of(cause, TENANT), "opened_at": OPENED_AT, "resolved_at": None}

    assert _alert_of(row).cause == cause  # type: ignore[arg-type]  # a dict stands for the row mapping of a query


def test_an_empty_filter_does_not_narrow() -> None:
    assert _admitted(AlertFilter()) == []


def test_a_filter_narrows_by_state_severity_resource_and_period() -> None:
    until = OPENED_AT + timedelta(hours=1)
    criteria = AlertFilter(AlertState.OPEN, AlertSeverity.WARNING, AlertResourceKind.ACCOUNT, ACCOUNT, OPENED_AT, until)

    state, severity, resource_kind, resource, since, before = _admitted(criteria)

    assert sql_of(state) == "alerts.resolved_at IS NULL"
    assert params_of(severity) == [["key_expiring", "unattributable_fill", "unattributable_position"]]
    assert params_of(resource_kind) == ["account"]
    assert params_of(resource) == [ACCOUNT]
    assert (">=" in sql_of(since), params_of(since)) == (True, [OPENED_AT])
    assert ("opened_at <" in sql_of(before), params_of(before)) == (True, [until])


def test_the_resolved_alerts_are_those_with_an_instant_of_resolution() -> None:
    [state] = _admitted(AlertFilter(state=AlertState.RESOLVED))

    assert sql_of(state) == "alerts.resolved_at IS NOT NULL"


def test_the_first_page_starts_from_the_newest_and_the_next_after_its_cursor() -> None:
    assert _after(None) == []
    [after] = _after(AlertCursor(OPENED_AT, uuid4()))
    assert "(alerts.opened_at, alerts.id) <" in sql_of(after)
