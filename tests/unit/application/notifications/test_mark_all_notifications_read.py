from uuid import uuid4

from autotrading.application.notifications.mark_all_notifications_read import MarkAllNotificationsReadUseCase
from autotrading.domain.notifications.notification import Notification
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.notification_inbox import START, InboxStore, InMemoryNotificationInboxAdapter


def test_every_notification_of_the_tenant_is_read_and_none_of_another() -> None:
    store: InboxStore = {}
    inbox = InMemoryNotificationInboxAdapter(store, TenantId.new())
    other = InMemoryNotificationInboxAdapter(store, TenantId.new())
    for flow in ("alfa", "beta"):
        inbox.add(Notification.cycle_failed(uuid4(), flow, "timeout"), START)
    other.add(Notification.test(), START)

    MarkAllNotificationsReadUseCase(inbox).execute()

    assert [each.is_read for each in inbox.notifications] == [True, True]
    assert other.unread_count() == 1
