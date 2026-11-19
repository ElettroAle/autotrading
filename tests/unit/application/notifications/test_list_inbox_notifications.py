from datetime import timedelta
from uuid import uuid4

from autotrading.application.notifications.list_inbox_notifications import (
    ListInboxNotificationsCommand,
    ListInboxNotificationsUseCase,
)
from autotrading.domain.notifications.inbox_page import INBOX_PAGE_SIZE
from autotrading.domain.notifications.notification import Notification
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.notification_inbox import START, InboxStore, InMemoryNotificationInboxAdapter


def failed(flow: str) -> Notification:
    return Notification.cycle_failed(uuid4(), flow, "timeout")


def test_the_bell_lists_the_notifications_of_the_tenant_newest_first_by_pages() -> None:
    store: InboxStore = {}
    tenant, other = TenantId.new(), TenantId.new()
    inbox = InMemoryNotificationInboxAdapter(store, tenant)
    for minute in range(INBOX_PAGE_SIZE + 1):
        inbox.add(failed(f"flusso-{minute}"), START + timedelta(minutes=minute))
    InMemoryNotificationInboxAdapter(store, other).add(failed("beta"), START + timedelta(hours=1))
    use_case = ListInboxNotificationsUseCase(inbox)

    first = use_case.execute(ListInboxNotificationsCommand())
    rest = use_case.execute(ListInboxNotificationsCommand(first.next))

    assert first.notifications[0].title == f"flusso-{INBOX_PAGE_SIZE}: ciclo fallito"
    assert len(first.notifications) == INBOX_PAGE_SIZE
    assert [notification.title for notification in rest.notifications] == ["flusso-0: ciclo fallito"]
    assert rest.next is None
