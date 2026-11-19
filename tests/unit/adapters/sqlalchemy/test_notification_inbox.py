from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.sql import ClauseElement

from autotrading.adapters.outbound.sqlalchemy.notification_inbox import _after, _inbox_notification_of, _row_of
from autotrading.domain.notifications.inbox_notification import InboxNotification
from autotrading.domain.notifications.inbox_page import InboxCursor
from autotrading.domain.notifications.notification import Amount, Notification
from autotrading.domain.tenancy.tenant_id import TenantId

NOTIFIED_AT = datetime(2026, 11, 19, 9, 0, tzinfo=UTC)
CLOSED_AT = datetime(2026, 11, 19, 8, 30, tzinfo=UTC)
TENANT = TenantId.new()
FLOW = uuid4()


def sql_of(clause: ClauseElement) -> str:
    return str(clause.compile())


def test_a_notification_is_read_back_with_its_pages_and_its_instants() -> None:
    closing = Notification.position_closed(FLOW, "alfa", "BTC", Amount(Decimal(1), "USDC"), "agente", CLOSED_AT)
    kept = InboxNotification.of(closing, NOTIFIED_AT)
    read_at = NOTIFIED_AT + timedelta(minutes=5)
    row = {**_row_of(kept, TENANT), "read_at": read_at}

    read_back = _inbox_notification_of(row)  # type: ignore[arg-type]  # a dict stands for the row mapping of a query

    assert row["tenant_id"] == TENANT.value
    assert read_back == kept.read(read_at)


def test_an_unread_notification_without_pages_is_read_back_unread() -> None:
    kept = InboxNotification.of(Notification.test(), NOTIFIED_AT)
    row = {**_row_of(kept, TENANT), "read_at": None}

    assert _inbox_notification_of(row) == kept  # type: ignore[arg-type]  # a dict stands for the row mapping of a query


def test_the_first_page_starts_from_the_newest_and_the_next_after_its_cursor() -> None:
    assert _after(None) == []
    [after] = _after(InboxCursor(NOTIFIED_AT, uuid4()))
    assert "(inbox_notifications.notified_at, inbox_notifications.id) <" in sql_of(after)
