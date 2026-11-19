"""ADR notifiche-nell-app-salvate-per-tenant: the bell on PostgreSQL, isolated by row level security, read one by one
or all at once, and forgotten 90 days after each notification."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import Engine

from autotrading.adapters.outbound.sqlalchemy.notification_inbox import SqlAlchemyNotificationInboxAdapter
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.application.notifications.errors import InboxNotificationNotFoundError
from autotrading.domain.notifications.inbox_notification import INBOX_RETENTION, InboxNotificationId
from autotrading.domain.notifications.inbox_page import INBOX_PAGE_SIZE
from autotrading.domain.notifications.notification import Amount, Notification
from autotrading.domain.notifications.notification_target import NotificationTarget
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.user_id import UserId

pytestmark = pytest.mark.integration

NINE = datetime(2026, 11, 19, 9, 0, tzinfo=UTC)
FLOW = uuid4()


def new_tenant(database: Engine) -> SqlAlchemyNotificationInboxAdapter:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    return SqlAlchemyNotificationInboxAdapter(database, tenant.id)


def failed(flow: str) -> Notification:
    return Notification.cycle_failed(FLOW, flow, "timeout")


def test_a_notification_is_kept_unread_with_its_pages_and_read_back(database: Engine) -> None:
    inbox = new_tenant(database)
    closed_at = NINE - timedelta(minutes=30)
    closing = Notification.position_closed(FLOW, "alfa", "BTC", Amount(Decimal(1), "USDC"), "agente", closed_at)

    inbox.add(closing, NINE)

    [kept] = inbox.list(None).notifications
    assert (kept.title, kept.text, kept.notified_at, kept.read_at) == (
        closing.heading,
        "\n".join(closing.body_lines()),
        NINE,
        None,
    )
    assert kept.targets == (NotificationTarget.flow(FLOW), NotificationTarget.closed_position(FLOW, "BTC", closed_at))
    assert inbox.unread_count() == 1


def test_the_bell_goes_by_pages_newest_first(database: Engine) -> None:
    inbox = new_tenant(database)
    for minute in range(INBOX_PAGE_SIZE + 1):
        inbox.add(failed(f"flusso-{minute}"), NINE + timedelta(minutes=minute))

    first = inbox.list(None)
    rest = inbox.list(first.next)

    assert len(first.notifications) == INBOX_PAGE_SIZE
    assert first.notifications[0].title == f"flusso-{INBOX_PAGE_SIZE}: ciclo fallito"
    assert [kept.title for kept in rest.notifications] == ["flusso-0: ciclo fallito"]
    assert rest.next is None


def test_a_notification_is_read_once_and_keeps_its_first_reading(database: Engine) -> None:
    inbox = new_tenant(database)
    inbox.add(failed("alfa"), NINE)
    inbox.add(failed("beta"), NINE + timedelta(minutes=1))
    beta, alfa = inbox.list(None).notifications

    inbox.mark_read(alfa.id)
    read_at = inbox.list(None).notifications[1].read_at
    inbox.mark_read(alfa.id)

    assert [kept.read_at is None for kept in inbox.list(None).notifications] == [True, False]
    assert inbox.list(None).notifications[1].read_at == read_at
    assert inbox.unread_count() == 1
    assert beta.read_at is None


def test_every_notification_is_read_at_once(database: Engine) -> None:
    inbox = new_tenant(database)
    inbox.add(failed("alfa"), NINE)
    inbox.add(failed("beta"), NINE + timedelta(minutes=1))

    inbox.mark_all_read()

    assert inbox.unread_count() == 0
    assert all(kept.is_read for kept in inbox.list(None).notifications)


def test_a_notification_of_another_tenant_is_not_found_and_never_listed(database: Engine) -> None:
    anna, bruno = new_tenant(database), new_tenant(database)
    bruno.add(failed("beta"), NINE)
    [theirs] = bruno.list(None).notifications

    with pytest.raises(InboxNotificationNotFoundError):
        anna.mark_read(theirs.id)
    anna.mark_all_read()

    assert anna.list(None).notifications == ()
    assert (anna.unread_count(), bruno.unread_count()) == (0, 1)


def test_a_notification_that_does_not_exist_is_not_found(database: Engine) -> None:
    with pytest.raises(InboxNotificationNotFoundError):
        new_tenant(database).mark_read(InboxNotificationId.new())


def test_keeping_a_notification_forgets_those_older_than_the_retention(database: Engine) -> None:
    anna, bruno = new_tenant(database), new_tenant(database)
    anna.add(failed("vecchio"), NINE)
    anna.add(failed("al-limite"), NINE + timedelta(seconds=1))
    bruno.add(failed("di-bruno"), NINE)

    anna.add(failed("nuovo"), NINE + INBOX_RETENTION + timedelta(seconds=1))

    assert [kept.title for kept in anna.list(None).notifications] == [
        "nuovo: ciclo fallito",
        "al-limite: ciclo fallito",
    ]
    assert [kept.title for kept in bruno.list(None).notifications] == ["di-bruno: ciclo fallito"]
