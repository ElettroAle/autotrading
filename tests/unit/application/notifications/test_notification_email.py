"""The address of the notifications by email: indicated, changed and removed by the user, and the emails that leave
from the mail server of the tenant (R3.5.2, R3.5.5, ADR invio-dal-server-di-posta-del-tenant).
"""

import logging
from collections.abc import Callable
from uuid import uuid4

import pytest

from autotrading.application.notifications.deliver_outbox_message import DeliverOutboxMessageUseCase
from autotrading.application.notifications.errors import (
    EmailNotDeliveredError,
    MailPasswordNotOpenedError,
    MailServerNotConfiguredError,
    OutboxUnavailableError,
)
from autotrading.application.notifications.get_notification_email import (
    MAIL_SERVER_MISSING,
    GetNotificationEmailUseCase,
    NotificationEmailSettings,
)
from autotrading.application.notifications.notify import NotifyUseCase
from autotrading.application.notifications.remove_notification_email import RemoveNotificationEmailUseCase
from autotrading.application.notifications.set_notification_email import (
    SetNotificationEmailCommand,
    SetNotificationEmailUseCase,
)
from autotrading.domain.notifications.channel_preferences import ChannelPreferences
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.email_address import EmailAddress
from autotrading.domain.notifications.errors import InvalidEmailAddressError
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.notifications.notification import Notification
from autotrading.domain.notifications.notification_channel import NotificationChannel
from autotrading.domain.notifications.notification_email import NotificationEmail
from autotrading.domain.notifications.notification_event import NotificationEvent
from autotrading.domain.notifications.outbox_message import CHAT_MESSAGE, EMAIL_MESSAGE, OutboxMessage
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.linked_chat_repository import InMemoryLinkedChatRepositoryAdapter, LinkedChatStore
from tests.fakes.mailer import FakeMailerAdapter, MailLogin, SentEmail
from tests.fakes.messenger import FakeMessengerAdapter
from tests.fakes.notification_email_repository import (
    InMemoryNotificationEmailRepositoryAdapter,
    NotificationEmailStore,
)
from tests.fakes.outbox import InMemoryOutboxAdapter, OutboxState
from tests.support.mail_servers import PASSWORD, MailServers
from tests.support.notifications import notification_routes

ANNA, BRUNO = TenantId.new(), TenantId.new()
ANNA_ADDRESS = EmailAddress.parse("anna@example.com")
PAUSED = Notification.flow_paused(uuid4(), "alfa", "credito esaurito", uuid4())
PAUSED_EVENT = NotificationEvent.FLOW_PAUSED
FAILED_EMAIL = "invio dell'email fallito"


class FailingOnEmailOutbox:
    """An outbox that keeps the messages to the chats and refuses the emails."""

    def __init__(self, outbox: InMemoryOutboxAdapter) -> None:
        self._outbox = outbox

    def enqueue(self, message: OutboxMessage) -> None:
        if message.integration == EMAIL_MESSAGE:
            raise OutboxUnavailableError
        self._outbox.enqueue(message)

    def process(self, deliver: Callable[[OutboxMessage], None]) -> None:
        self._outbox.process(deliver)


class Mail:
    """The addresses, the chats, the outbox and the mail servers of one test; the outbox delivers at once."""

    def __init__(self) -> None:
        self.emails: NotificationEmailStore = {}
        self.chats: LinkedChatStore = {}
        self.servers = MailServers()
        self.mailer = FakeMailerAdapter()
        self.messenger = FakeMessengerAdapter()
        self.outbox = InMemoryOutboxAdapter()
        self.outbox.process(DeliverOutboxMessageUseCase(self.messenger, self.mailer, self.servers.access_of).execute)

    def repository(self, tenant_id: TenantId) -> InMemoryNotificationEmailRepositoryAdapter:
        return InMemoryNotificationEmailRepositoryAdapter(self.emails, tenant_id)

    def indicate(self, tenant_id: TenantId, address: str) -> None:
        SetNotificationEmailUseCase(tenant_id, self.repository(tenant_id)).execute(SetNotificationEmailCommand(address))

    def settings(self, tenant_id: TenantId) -> NotificationEmailSettings:
        return GetNotificationEmailUseCase(self.repository(tenant_id), self.servers.repository(tenant_id)).execute()

    def configure(self, tenant_id: TenantId, username: str = "anna@example.com") -> None:
        self.servers.configure(tenant_id, username)

    def notify_for(self, tenant_id: TenantId, outbox: InMemoryOutboxAdapter | FailingOnEmailOutbox) -> NotifyUseCase:
        chats = InMemoryLinkedChatRepositoryAdapter(self.chats, tenant_id)
        # The tenant chose both channels for the event: R3.5.3 sends each event only on its channel.
        both = {tenant_id: ChannelPreferences.of(tenant_id).choosing(PAUSED_EVENT, frozenset(NotificationChannel))}
        servers = self.servers.repository(tenant_id)
        return NotifyUseCase(chats, self.repository(tenant_id), servers, outbox, notification_routes(tenant_id, both))

    def notify(self, tenant_id: TenantId, notification: Notification = PAUSED) -> None:
        self.notify_for(tenant_id, self.outbox).execute(notification)


@pytest.fixture
def mail() -> Mail:
    return Mail()


def test_an_indicated_address_is_the_address_of_the_tenant(mail: Mail) -> None:
    mail.configure(ANNA)
    mail.indicate(ANNA, " anna@example.com ")

    assert mail.settings(ANNA) == NotificationEmailSettings(ANNA_ADDRESS, None)
    assert mail.emails == {ANNA: NotificationEmail(ANNA, ANNA_ADDRESS)}


def test_a_new_address_replaces_the_previous_one(mail: Mail) -> None:
    mail.indicate(ANNA, "anna@example.com")

    mail.indicate(ANNA, "anna2@example.com")

    assert mail.settings(ANNA).address == EmailAddress.parse("anna2@example.com")


def test_an_address_without_the_form_of_an_email_is_refused_and_keeps_the_previous_one(mail: Mail) -> None:
    mail.indicate(ANNA, "anna@example.com")

    with pytest.raises(InvalidEmailAddressError):
        mail.indicate(ANNA, "anna@")

    assert mail.settings(ANNA).address == ANNA_ADDRESS


def test_a_removed_address_is_no_more_and_removing_again_is_no_error(mail: Mail) -> None:
    mail.indicate(ANNA, "anna@example.com")
    remove = RemoveNotificationEmailUseCase(mail.repository(ANNA))

    remove.execute()
    remove.execute()

    assert mail.settings(ANNA).address is None


def test_without_a_mail_server_the_settings_keep_the_address_and_warn_that_no_email_leaves(mail: Mail) -> None:
    mail.indicate(ANNA, "anna@example.com")

    assert mail.settings(ANNA) == NotificationEmailSettings(ANNA_ADDRESS, MAIL_SERVER_MISSING)
    assert MAIL_SERVER_MISSING == "le email non partono: server di posta non configurato"


def test_with_a_mail_server_the_settings_do_not_warn(mail: Mail) -> None:
    mail.indicate(ANNA, "anna@example.com")
    mail.configure(ANNA)

    assert mail.settings(ANNA).warning is None


def test_a_notification_goes_by_email_with_the_event_as_subject_and_the_text_of_the_chat(mail: Mail) -> None:
    mail.indicate(ANNA, "anna@example.com")
    mail.configure(ANNA)

    mail.notify(ANNA)

    assert mail.mailer.sent == [SentEmail(ANNA_ADDRESS, PAUSED.title, PAUSED.text)]


def test_a_notification_leaves_from_the_mail_server_of_its_tenant_with_its_opened_password(mail: Mail) -> None:
    mail.indicate(ANNA, "anna@example.com")
    mail.configure(ANNA)
    mail.servers.configure(BRUNO, "bruno@example.com", host="smtp.bruno.example.com")

    mail.notify(ANNA)

    assert mail.mailer.logins == [MailLogin("smtp.example.com", 587, "anna@example.com", PASSWORD, "anna@example.com")]


def test_a_notification_goes_to_the_chat_and_to_the_address_of_its_tenant_only(mail: Mail) -> None:
    mail.indicate(ANNA, "anna@example.com")
    mail.indicate(BRUNO, "bruno@example.com")
    mail.configure(ANNA)
    mail.configure(BRUNO, "bruno@example.com")
    mail.chats[ANNA] = LinkedChat(ANNA, ChatId(1001))

    mail.notify(ANNA)

    assert [message.integration for message in mail.outbox.messages] == [CHAT_MESSAGE, EMAIL_MESSAGE]
    assert mail.messenger.sent == [(ChatId(1001), PAUSED.text)]
    assert mail.mailer.received_by("bruno@example.com") == []


def test_without_an_address_or_without_a_mail_server_no_email_is_queued(mail: Mail) -> None:
    mail.configure(ANNA)
    mail.notify(ANNA)
    mail.indicate(ANNA, "anna@example.com")
    mail.servers.store.clear()
    mail.notify(ANNA)

    assert mail.outbox.messages == []


def test_an_email_the_outbox_does_not_take_is_recorded_and_the_chat_still_gets_its_message(
    mail: Mail, caplog: pytest.LogCaptureFixture
) -> None:
    mail.indicate(ANNA, "anna@example.com")
    mail.configure(ANNA)
    mail.chats[ANNA] = LinkedChat(ANNA, ChatId(1001))

    with caplog.at_level(logging.WARNING, logger="autotrading.notifications"):
        mail.notify_for(ANNA, FailingOnEmailOutbox(mail.outbox)).execute(PAUSED)

    [record] = caplog.records
    assert record.getMessage() == "notifica non accodata"
    assert (record.__dict__["tenant_id"], record.__dict__["subject"]) == (str(ANNA.value), "alfa")
    assert mail.messenger.sent == [(ChatId(1001), PAUSED.text)]


def test_an_email_the_mail_server_refuses_is_recorded_and_left_to_the_retries(
    mail: Mail, caplog: pytest.LogCaptureFixture
) -> None:
    mail.indicate(ANNA, "anna@example.com")
    mail.configure(ANNA)
    mail.mailer.accepting = False

    with caplog.at_level(logging.WARNING, logger="autotrading.notifications"):
        mail.notify(ANNA)

    [record] = caplog.records
    [message] = mail.outbox.messages
    assert record.getMessage() == FAILED_EMAIL
    assert (record.__dict__["tenant_id"], record.__dict__["message_id"]) == (str(ANNA.value), str(message.id.value))
    assert mail.outbox.in_state(OutboxState.PENDING) == [message]


def an_email_of(tenant_id: TenantId) -> OutboxMessage:
    return OutboxMessage.to_email(NotificationEmail(tenant_id, ANNA_ADDRESS), "s", "t")


def test_the_delivery_of_an_email_raises_the_transient_error_of_the_mail_server(mail: Mail) -> None:
    mail.configure(ANNA)
    mail.mailer.accepting = False
    deliver = DeliverOutboxMessageUseCase(FakeMessengerAdapter(), mail.mailer, mail.servers.access_of)

    with pytest.raises(EmailNotDeliveredError, match=r"^email non consegnata$") as raised:
        deliver.execute(an_email_of(ANNA))

    assert not raised.value.permanent
    assert raised.value.status_code == 503


def test_an_email_of_a_tenant_without_a_mail_server_fails_and_is_recorded(
    mail: Mail, caplog: pytest.LogCaptureFixture
) -> None:
    mail.configure(BRUNO, "bruno@example.com")
    deliver = DeliverOutboxMessageUseCase(FakeMessengerAdapter(), mail.mailer, mail.servers.access_of)

    with (
        caplog.at_level(logging.WARNING, logger="autotrading.notifications"),
        pytest.raises(MailServerNotConfiguredError) as raised,
    ):
        deliver.execute(an_email_of(ANNA))

    assert not raised.value.permanent
    assert [record.getMessage() for record in caplog.records] == [FAILED_EMAIL]
    assert mail.mailer.sent == []


def test_an_email_whose_password_cannot_be_opened_fails_and_is_recorded(
    mail: Mail, caplog: pytest.LogCaptureFixture
) -> None:
    mail.configure(ANNA)
    mail.servers.vault.clear()
    deliver = DeliverOutboxMessageUseCase(FakeMessengerAdapter(), mail.mailer, mail.servers.access_of)

    with (
        caplog.at_level(logging.WARNING, logger="autotrading.notifications"),
        pytest.raises(MailPasswordNotOpenedError),
    ):
        deliver.execute(an_email_of(ANNA))

    assert [record.getMessage() for record in caplog.records] == [FAILED_EMAIL]
