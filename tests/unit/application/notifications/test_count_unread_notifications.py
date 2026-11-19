from uuid import uuid4

from autotrading.application.notifications.count_unread_notifications import CountUnreadNotificationsUseCase
from autotrading.domain.notifications.notification import Notification
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.notification_inbox import START, InboxStore, InMemoryNotificationInboxAdapter


def test_only_the_unread_notifications_of_the_tenant_count() -> None:
    store: InboxStore = {}
    tenant, other = TenantId.new(), TenantId.new()
    inbox = InMemoryNotificationInboxAdapter(store, tenant)
    for flow in ("alfa", "beta", "gamma"):
        inbox.add(Notification.cycle_failed(uuid4(), flow, "timeout"), START)
    inbox.mark_read(inbox.notifications[0].id)
    InMemoryNotificationInboxAdapter(store, other).add(Notification.test(), START)

    assert CountUnreadNotificationsUseCase(inbox).execute() == 2
