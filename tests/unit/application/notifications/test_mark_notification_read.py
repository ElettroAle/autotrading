from datetime import timedelta
from uuid import uuid4

import pytest

from autotrading.application.notifications.errors import InboxNotificationNotFoundError
from autotrading.application.notifications.mark_notification_read import (
    MarkNotificationReadCommand,
    MarkNotificationReadUseCase,
)
from autotrading.domain.notifications.inbox_notification import InboxNotificationId
from autotrading.domain.notifications.notification import Notification
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.notification_inbox import START, InboxStore, InMemoryNotificationInboxAdapter

READ_AT = START + timedelta(minutes=5)


def test_the_chosen_notification_alone_is_read() -> None:
    inbox = InMemoryNotificationInboxAdapter({}, TenantId.new(), lambda: READ_AT)
    inbox.add(Notification.test(), START)
    inbox.add(Notification.cycle_failed(uuid4(), "alfa", "timeout"), START)
    chosen, other = inbox.notifications

    MarkNotificationReadUseCase(inbox).execute(MarkNotificationReadCommand(chosen.id))

    assert [(each.id, each.read_at) for each in inbox.notifications] == [(chosen.id, READ_AT), (other.id, None)]


def test_a_notification_of_another_tenant_is_not_found_and_stays_unread() -> None:
    store: InboxStore = {}
    theirs = InMemoryNotificationInboxAdapter(store, TenantId.new())
    theirs.add(Notification.test(), START)
    mine = InMemoryNotificationInboxAdapter(store, TenantId.new())

    with pytest.raises(InboxNotificationNotFoundError):
        MarkNotificationReadUseCase(mine).execute(MarkNotificationReadCommand(theirs.notifications[0].id))

    assert not theirs.notifications[0].is_read


def test_a_notification_that_does_not_exist_is_not_found() -> None:
    inbox = InMemoryNotificationInboxAdapter({}, TenantId.new())

    with pytest.raises(InboxNotificationNotFoundError):
        MarkNotificationReadUseCase(inbox).execute(MarkNotificationReadCommand(InboxNotificationId.new()))
