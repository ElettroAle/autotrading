"""ADR destinazioni-delle-notifiche-nella-dashboard and ADR link-nei-messaggi-telegram-ed-email: the links of a
notification reach every channel with its message (R3.5.6).
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from autotrading.application.notifications.deliver_outbox_message import DeliverOutboxMessageUseCase
from autotrading.application.notifications.notify import NotifyUseCase
from autotrading.domain.notifications.channel_preferences import ChannelPreferences
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.email_address import EmailAddress
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.notifications.notification import Amount, Notification
from autotrading.domain.notifications.notification_channel import NotificationChannel
from autotrading.domain.notifications.notification_email import NotificationEmail
from autotrading.domain.notifications.notification_event import NotificationEvent
from autotrading.domain.notifications.notification_link import NotificationLink
from autotrading.domain.notifications.notification_target import NotificationTarget
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.linked_chat_repository import InMemoryLinkedChatRepositoryAdapter
from tests.fakes.mailer import FakeMailerAdapter
from tests.fakes.messenger import FakeMessengerAdapter
from tests.fakes.notification_email_repository import InMemoryNotificationEmailRepositoryAdapter
from tests.fakes.notification_link import FakeNotificationLinkAdapter
from tests.fakes.outbox import InMemoryOutboxAdapter
from tests.support.mail_servers import MailServers
from tests.support.notifications import notification_routes

ANNA = TenantId.new()
CHAT = ChatId(1001)
ADDRESS = "anna@example.com"
FLOW_ID = uuid4()
CLOSED_AT = datetime(2026, 11, 17, 10, 15, tzinfo=UTC)
CLOSED = Notification.position_closed(FLOW_ID, "alfa", "BTC", Amount(Decimal(4), "USDC"), "take profit", CLOSED_AT)


class Channels:
    """Anna reached on Telegram and by email, every event on both, with or without a dashboard to lead to."""

    def __init__(self, *, dashboard: bool = True) -> None:
        self.messenger = FakeMessengerAdapter()
        self.mailer = FakeMailerAdapter()
        self.mail_servers = MailServers()
        self.mail_servers.configure(ANNA, ADDRESS)
        self.links = FakeNotificationLinkAdapter(dashboard=dashboard)
        self.outbox = InMemoryOutboxAdapter()
        self.outbox.process(
            DeliverOutboxMessageUseCase(self.messenger, self.mailer, self.mail_servers.access_of).execute
        )

    def notify(self, notification: Notification) -> None:
        preferences = ChannelPreferences.of(ANNA)
        for event in NotificationEvent:
            preferences = preferences.choosing(event, frozenset(NotificationChannel))
        NotifyUseCase(
            InMemoryLinkedChatRepositoryAdapter({ANNA: LinkedChat(ANNA, CHAT)}, ANNA),
            InMemoryNotificationEmailRepositoryAdapter(
                {ANNA: NotificationEmail(ANNA, EmailAddress.parse(ADDRESS))}, ANNA
            ),
            self.mail_servers.repository(ANNA),
            self.outbox,
            notification_routes(ANNA, {ANNA: preferences}, self.links),
        ).execute(notification)

    def link_to(self, target: NotificationTarget) -> NotificationLink:
        return NotificationLink(target.label, self.links.address_of(target))


def test_the_message_on_telegram_carries_a_link_for_each_page_in_their_order() -> None:
    channels = Channels()

    channels.notify(CLOSED)

    assert channels.messenger.links_received_by(CHAT) == [
        (
            channels.link_to(NotificationTarget.flow(FLOW_ID)),
            channels.link_to(NotificationTarget.closed_position(FLOW_ID, "BTC", CLOSED_AT)),
        )
    ]
    assert channels.messenger.received_by(CHAT) == [CLOSED.text]


def test_the_email_ends_with_the_links_after_the_text_of_the_notification() -> None:
    channels = Channels()

    channels.notify(CLOSED)

    [email] = channels.mailer.received_by(ADDRESS)
    flow = channels.link_to(NotificationTarget.flow(FLOW_ID))
    position = channels.link_to(NotificationTarget.closed_position(FLOW_ID, "BTC", CLOSED_AT))
    assert email.subject == CLOSED.title
    assert email.text == f"{CLOSED.text}\n\nApri flusso: {flow.url}\nApri operazione: {position.url}"


def test_without_a_dashboard_the_notification_leaves_without_links() -> None:
    channels = Channels(dashboard=False)

    channels.notify(CLOSED)

    assert channels.messenger.links_received_by(CHAT) == [()]
    assert [email.text for email in channels.mailer.received_by(ADDRESS)] == [CLOSED.text]
    assert all("links" not in message.payload for message in channels.outbox.messages)


def test_a_notification_that_leads_nowhere_leaves_without_links() -> None:
    channels = Channels()

    channels.notify(Notification.test())

    assert channels.messenger.links_received_by(CHAT) == [()]
