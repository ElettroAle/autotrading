"""Every notification goes to the bell of the tenant, before and whatever its channels (R6.2.1, ADR
notifiche-nell-app-salvate-per-tenant)."""

import logging
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from autotrading.application.notifications.notify import NotifyUseCase
from autotrading.application.notifications.ports import NotificationInbox
from autotrading.domain.notifications.channel_preferences import ChannelPreferences
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.inbox_notification import InboxNotification
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.notifications.notification import Notification
from autotrading.domain.notifications.notification_event import NotificationEvent
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.channel_preferences_repository import ChannelPreferencesStore
from tests.fakes.cycles import FakeClockAdapter
from tests.fakes.linked_chat_repository import InMemoryLinkedChatRepositoryAdapter, LinkedChatStore
from tests.fakes.notification_email_repository import InMemoryNotificationEmailRepositoryAdapter
from tests.fakes.notification_inbox import InboxStore, InMemoryNotificationInboxAdapter
from tests.fakes.outbox import InMemoryOutboxAdapter
from tests.support.mail_servers import MailServers
from tests.support.notifications import notification_routes

NINE = datetime(2026, 11, 19, 9, 0, tzinfo=UTC)
ANNA, BRUNO = TenantId.new(), TenantId.new()
CHAT = ChatId(1001)
FAILED = Notification.cycle_failed(uuid4(), "alfa", "timeout")


class Worker:
    """The stores of the notifications of one test, the bell of every tenant among them."""

    def __init__(self) -> None:
        self.chats: LinkedChatStore = {}
        self.preferences: ChannelPreferencesStore = {}
        self.inbox: InboxStore = {}
        self.outbox = InMemoryOutboxAdapter()
        self.clock = FakeClockAdapter(NINE)
        self.inbox_reachable = True

    def notify(self, tenant_id: TenantId, notification: Notification = FAILED) -> None:
        bell = InMemoryNotificationInboxAdapter(self.inbox, tenant_id, self.clock.now)
        bell.reachable = self.inbox_reachable
        NotifyUseCase(
            InMemoryLinkedChatRepositoryAdapter(self.chats, tenant_id),
            InMemoryNotificationEmailRepositoryAdapter({}, tenant_id),
            MailServers().repository(tenant_id),
            self.outbox,
            notification_routes(tenant_id, self.preferences),
            NotificationInbox(bell, self.clock),
        ).execute(notification)

    def bell_of(self, tenant_id: TenantId) -> list[InboxNotification]:
        return self.inbox.get(tenant_id, [])


@pytest.fixture
def worker() -> Worker:
    return Worker()


def test_a_notification_without_a_channel_is_kept_in_the_bell_of_its_tenant(worker: Worker) -> None:
    worker.notify(ANNA)

    [kept] = worker.bell_of(ANNA)
    assert (kept.title, kept.notified_at, kept.is_read) == (FAILED.heading, NINE, False)
    assert worker.outbox.messages == []
    assert worker.bell_of(BRUNO) == []


def test_a_notification_on_a_channel_is_kept_in_the_bell_too(worker: Worker) -> None:
    worker.chats[ANNA] = LinkedChat(ANNA, CHAT)

    worker.notify(ANNA)

    assert [message.chat_message().text for message in worker.outbox.messages] == [FAILED.text]
    assert [kept.title for kept in worker.bell_of(ANNA)] == [FAILED.heading]


def test_an_event_with_no_channel_chosen_is_kept_in_the_bell(worker: Worker) -> None:
    worker.chats[ANNA] = LinkedChat(ANNA, CHAT)
    worker.preferences[ANNA] = ChannelPreferences.of(ANNA).choosing(NotificationEvent.CYCLE_FAILED, frozenset())

    worker.notify(ANNA)

    assert worker.outbox.messages == []
    assert [kept.title for kept in worker.bell_of(ANNA)] == [FAILED.heading]


def test_the_test_notification_is_kept_in_the_bell(worker: Worker) -> None:
    worker.notify(ANNA, Notification.test())

    assert [kept.title for kept in worker.bell_of(ANNA)] == [Notification.test().heading]


def test_a_bell_out_of_reach_is_recorded_and_the_channels_get_their_message(
    worker: Worker, caplog: pytest.LogCaptureFixture
) -> None:
    worker.chats[ANNA] = LinkedChat(ANNA, CHAT)
    worker.inbox_reachable = False

    with caplog.at_level(logging.WARNING, logger="autotrading.notifications"):
        worker.notify(ANNA)

    assert [message.chat_message().text for message in worker.outbox.messages] == [FAILED.text]
    assert worker.bell_of(ANNA) == []
    [record] = [record for record in caplog.records if record.getMessage() == "notifica non salvata nel campanello"]
    assert record.__dict__["subject"] == FAILED.subject
