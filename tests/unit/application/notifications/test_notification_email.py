"""The address of the notifications by email: indicated, changed and removed by the user, and the test email (R3.5.2,
ADR canale-email-delle-notifiche-con-smtp).
"""

import logging
from collections.abc import Callable

import pytest

from autotrading.application.notifications.deliver_outbox_message import DeliverOutboxMessageUseCase
from autotrading.application.notifications.errors import (
    EmailNotDeliveredError,
    MailServiceNotConfiguredError,
    NoNotificationEmailToTestError,
    OutboxUnavailableError,
)
from autotrading.application.notifications.get_notification_email import (
    MAIL_SERVICE_MISSING,
    GetNotificationEmailUseCase,
    NotificationEmailSettings,
)
from autotrading.application.notifications.notify import NotifyUseCase
from autotrading.application.notifications.remove_notification_email import RemoveNotificationEmailUseCase
from autotrading.application.notifications.send_test_email import SendTestEmailUseCase
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
from tests.fakes.mail_service import FakeMailServiceAdapter
from tests.fakes.mailer import FakeMailerAdapter, SentEmail
from tests.fakes.messenger import FakeMessengerAdapter
from tests.fakes.notification_email_repository import (
    InMemoryNotificationEmailRepositoryAdapter,
    NotificationEmailStore,
)
from tests.fakes.outbox import InMemoryOutboxAdapter, OutboxState
from tests.support.notifications import channel_choices

ANNA, BRUNO = TenantId.new(), TenantId.new()
ANNA_ADDRESS = EmailAddress.parse("anna@example.com")
PAUSED = Notification.flow_paused("alfa", "credito esaurito")
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
    """The addresses, the chats, the outbox and the mail service of one test; the outbox delivers at once."""

    def __init__(self) -> None:
        self.emails: NotificationEmailStore = {}
        self.chats: LinkedChatStore = {}
        self.service = FakeMailServiceAdapter()
        self.mailer = FakeMailerAdapter()
        self.messenger = FakeMessengerAdapter()
        self.outbox = InMemoryOutboxAdapter()
        self.outbox.process(DeliverOutboxMessageUseCase(self.messenger, self.mailer).execute)

    def repository(self, tenant_id: TenantId) -> InMemoryNotificationEmailRepositoryAdapter:
        return InMemoryNotificationEmailRepositoryAdapter(self.emails, tenant_id)

    def indicate(self, tenant_id: TenantId, address: str) -> None:
        SetNotificationEmailUseCase(tenant_id, self.repository(tenant_id)).execute(SetNotificationEmailCommand(address))

    def settings(self, tenant_id: TenantId) -> NotificationEmailSettings:
        return GetNotificationEmailUseCase(self.repository(tenant_id), self.service).execute()

    def ask_for_test(self, tenant_id: TenantId) -> None:
        SendTestEmailUseCase(self.repository(tenant_id), self.service, self.outbox).execute()

    def notify_for(self, tenant_id: TenantId, outbox: InMemoryOutboxAdapter | FailingOnEmailOutbox) -> NotifyUseCase:
        chats = InMemoryLinkedChatRepositoryAdapter(self.chats, tenant_id)
        # The tenant chose both channels for the event: R3.5.3 sends each event only on its channel.
        both = {tenant_id: ChannelPreferences.of(tenant_id).choosing(PAUSED_EVENT, NotificationChannel.BOTH)}
        return NotifyUseCase(chats, self.repository(tenant_id), self.service, outbox, channel_choices(tenant_id, both))

    def notify(self, tenant_id: TenantId, notification: Notification = PAUSED) -> None:
        self.notify_for(tenant_id, self.outbox).execute(notification)


@pytest.fixture
def mail() -> Mail:
    return Mail()


def test_an_indicated_address_is_the_address_of_the_tenant(mail: Mail) -> None:
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


def test_without_a_mail_service_the_settings_keep_the_address_and_warn_that_no_email_leaves(mail: Mail) -> None:
    mail.indicate(ANNA, "anna@example.com")
    mail.service.configured = False

    assert mail.settings(ANNA) == NotificationEmailSettings(ANNA_ADDRESS, MAIL_SERVICE_MISSING)
    assert MAIL_SERVICE_MISSING == "le email non partono: servizio di posta non configurato"


def test_the_test_email_reaches_the_address_of_the_tenant_by_the_outbox(mail: Mail) -> None:
    mail.indicate(ANNA, "anna@example.com")

    mail.ask_for_test(ANNA)

    [message] = mail.outbox.messages
    assert (message.tenant_id, message.integration) == (ANNA, EMAIL_MESSAGE)
    assert mail.mailer.sent == [
        SentEmail(
            ANNA_ADDRESS,
            "AutoTrading: prova delle notifiche",
            "notifica di prova: le notifiche dei tuoi flussi arrivano qui",
        )
    ]


def test_a_test_without_an_address_is_a_conflict_and_queues_nothing(mail: Mail) -> None:
    with pytest.raises(NoNotificationEmailToTestError, match=r"^nessun indirizzo email per le notifiche$") as raised:
        mail.ask_for_test(ANNA)

    assert raised.value.status_code == 409
    assert mail.outbox.messages == []


def test_a_test_without_a_mail_service_is_a_conflict_even_before_an_address(mail: Mail) -> None:
    mail.service.configured = False

    with pytest.raises(MailServiceNotConfiguredError, match=r"^servizio di posta non configurato$") as raised:
        mail.ask_for_test(ANNA)

    assert raised.value.status_code == 409
    assert mail.outbox.messages == []


def test_a_test_the_outbox_does_not_take_fails_for_the_user_to_ask_again(mail: Mail) -> None:
    mail.indicate(ANNA, "anna@example.com")
    mail.outbox.reachable = False

    with pytest.raises(OutboxUnavailableError):
        mail.ask_for_test(ANNA)


def test_a_notification_goes_by_email_with_the_event_as_subject_and_the_text_of_the_chat(mail: Mail) -> None:
    mail.indicate(ANNA, "anna@example.com")

    mail.notify(ANNA)

    assert mail.mailer.sent == [SentEmail(ANNA_ADDRESS, "alfa: in pausa", "alfa: in pausa, credito esaurito")]


def test_a_notification_goes_to_the_chat_and_to_the_address_of_its_tenant_only(mail: Mail) -> None:
    mail.indicate(ANNA, "anna@example.com")
    mail.indicate(BRUNO, "bruno@example.com")
    mail.chats[ANNA] = LinkedChat(ANNA, ChatId(1001))

    mail.notify(ANNA)

    assert [message.integration for message in mail.outbox.messages] == [CHAT_MESSAGE, EMAIL_MESSAGE]
    assert mail.messenger.sent == [(ChatId(1001), "alfa: in pausa, credito esaurito")]
    assert mail.mailer.received_by("bruno@example.com") == []


def test_without_an_address_or_without_a_mail_service_no_email_is_queued(mail: Mail) -> None:
    mail.notify(ANNA)
    mail.indicate(ANNA, "anna@example.com")
    mail.service.configured = False
    mail.notify(ANNA)

    assert mail.outbox.messages == []


def test_an_email_the_outbox_does_not_take_is_recorded_and_the_chat_still_gets_its_message(
    mail: Mail, caplog: pytest.LogCaptureFixture
) -> None:
    mail.indicate(ANNA, "anna@example.com")
    mail.chats[ANNA] = LinkedChat(ANNA, ChatId(1001))

    with caplog.at_level(logging.WARNING, logger="autotrading.notifications"):
        mail.notify_for(ANNA, FailingOnEmailOutbox(mail.outbox)).execute(PAUSED)

    [record] = caplog.records
    assert record.getMessage() == "notifica non accodata"
    assert (record.__dict__["tenant_id"], record.__dict__["subject"]) == (str(ANNA.value), "alfa")
    assert mail.messenger.sent == [(ChatId(1001), "alfa: in pausa, credito esaurito")]


def test_an_email_the_mail_service_refuses_is_recorded_and_left_to_the_retries(
    mail: Mail, caplog: pytest.LogCaptureFixture
) -> None:
    mail.indicate(ANNA, "anna@example.com")
    mail.mailer.accepting = False

    with caplog.at_level(logging.WARNING, logger="autotrading.notifications"):
        mail.notify(ANNA)

    [record] = caplog.records
    [message] = mail.outbox.messages
    assert record.getMessage() == FAILED_EMAIL
    assert (record.__dict__["tenant_id"], record.__dict__["message_id"]) == (str(ANNA.value), str(message.id.value))
    assert mail.outbox.in_state(OutboxState.PENDING) == [message]


def test_the_delivery_of_an_email_raises_the_transient_error_of_the_mail_service() -> None:
    mailer = FakeMailerAdapter()
    mailer.accepting = False
    message = OutboxMessage.to_email(NotificationEmail(ANNA, ANNA_ADDRESS), "s", "t")

    with pytest.raises(EmailNotDeliveredError, match=r"^email non consegnata$") as raised:
        DeliverOutboxMessageUseCase(FakeMessengerAdapter(), mailer).execute(message)

    assert not raised.value.permanent
    assert raised.value.status_code == 503
