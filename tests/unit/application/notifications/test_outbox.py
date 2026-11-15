"""A notification goes through the outbox: queued with its tenant, then delivered by integration (ADR
outbox-delle-integrazioni-esterne-con-procrastinate).
"""

import logging

import pytest

from autotrading.application.notifications.deliver_outbox_message import DeliverOutboxMessageUseCase
from autotrading.application.notifications.errors import MessageNotDeliveredError, UnknownOutboxIntegrationError
from autotrading.application.notifications.notify import NotifyUseCase
from autotrading.application.notifications.process_outbox import ProcessOutboxUseCase
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.errors import InvalidOutboxMessageError
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.notifications.notification import Notification
from autotrading.domain.notifications.outbox_message import CHAT_MESSAGE, OutboxMessage
from autotrading.domain.notifications.outbox_message_id import OutboxMessageId
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.linked_chat_repository import InMemoryLinkedChatRepositoryAdapter, LinkedChatStore
from tests.fakes.messenger import FakeMessengerAdapter
from tests.fakes.outbox import InMemoryOutboxAdapter, OutboxState

ANNA, BRUNO = TenantId.new(), TenantId.new()
CHAT, OTHER_CHAT = ChatId(1001), ChatId(2002)
FAILED = Notification.cycle_failed("alfa", "timeout")


class Outbox:
    """The chats, the outbox and the messenger of one test: the outbox delivers only once processing starts."""

    def __init__(self) -> None:
        self.chats: LinkedChatStore = {ANNA: LinkedChat(ANNA, CHAT), BRUNO: LinkedChat(BRUNO, OTHER_CHAT)}
        self.outbox = InMemoryOutboxAdapter()
        self.messenger = FakeMessengerAdapter()

    def notify(self, tenant_id: TenantId, notification: Notification = FAILED) -> None:
        NotifyUseCase(InMemoryLinkedChatRepositoryAdapter(self.chats, tenant_id), self.outbox).execute(notification)

    def process(self) -> None:
        ProcessOutboxUseCase(self.outbox, DeliverOutboxMessageUseCase(self.messenger)).execute()


@pytest.fixture
def box() -> Outbox:
    return Outbox()


def test_a_notification_is_queued_for_the_chat_of_its_tenant_and_not_sent_yet(box: Outbox) -> None:
    box.notify(ANNA)

    [message] = box.outbox.messages
    assert (message.tenant_id, message.integration) == (ANNA, CHAT_MESSAGE)
    assert message.payload == {"chat_id": CHAT.value, "text": "alfa: ciclo fallito, timeout"}
    assert box.messenger.sent == []


def test_without_a_linked_chat_nothing_is_queued(box: Outbox) -> None:
    del box.chats[ANNA]

    box.notify(ANNA)

    assert box.outbox.messages == []


def test_an_outbox_that_does_not_take_the_notification_is_recorded_without_failing(
    box: Outbox, caplog: pytest.LogCaptureFixture
) -> None:
    box.outbox.reachable = False

    with caplog.at_level(logging.WARNING, logger="autotrading.notifications"):
        box.notify(ANNA)

    [record] = caplog.records
    assert record.getMessage() == "notifica non accodata"
    assert (record.__dict__["tenant_id"], record.__dict__["subject"]) == (str(ANNA.value), "alfa")


def test_processing_delivers_each_queued_message_to_its_chat(box: Outbox) -> None:
    box.notify(ANNA)
    box.notify(BRUNO, Notification.test())

    box.process()

    assert box.messenger.sent == [
        (CHAT, "alfa: ciclo fallito, timeout"),
        (OTHER_CHAT, "notifica di prova: le notifiche dei tuoi flussi arrivano qui"),
    ]
    assert box.outbox.in_state(OutboxState.DELIVERED) == box.outbox.messages


def test_a_message_queued_while_processing_is_delivered_at_once(box: Outbox) -> None:
    box.process()

    box.notify(ANNA)

    assert box.messenger.received_by(CHAT) == ["alfa: ciclo fallito, timeout"]


def test_a_delivery_the_messenger_does_not_take_is_recorded_and_left_to_the_retries(
    box: Outbox, caplog: pytest.LogCaptureFixture
) -> None:
    box.messenger.reachable = False
    box.notify(ANNA)

    with caplog.at_level(logging.WARNING, logger="autotrading.notifications"):
        box.process()

    [record] = caplog.records
    assert record.getMessage() == "invio della notifica fallito"
    [message] = box.outbox.messages
    assert record.__dict__["tenant_id"] == str(ANNA.value)
    assert record.__dict__["message_id"] == str(message.id.value)
    assert box.outbox.in_state(OutboxState.PENDING) == [message]


def test_a_transient_failure_is_delivered_once_the_backoff_has_passed(box: Outbox) -> None:
    box.messenger.reachable = False
    box.notify(ANNA)
    box.process()
    box.messenger.reachable = True

    box.outbox.let_backoff_pass()

    assert box.messenger.received_by(CHAT) == ["alfa: ciclo fallito, timeout"]
    [message] = box.outbox.messages
    assert box.outbox.attempts[message.id] == 2


def test_the_delivery_of_a_message_raises_the_transient_error_of_the_messenger() -> None:
    messenger = FakeMessengerAdapter()
    messenger.reachable = False

    with pytest.raises(MessageNotDeliveredError) as raised:
        DeliverOutboxMessageUseCase(messenger).execute(OutboxMessage.to_chat(LinkedChat(ANNA, CHAT), "alfa"))

    assert not raised.value.permanent


def test_a_message_of_an_integration_without_its_port_fails_for_good() -> None:
    message = OutboxMessage(OutboxMessageId.new(), ANNA, "posta", {"to": "anna"})

    with pytest.raises(UnknownOutboxIntegrationError, match=r"^integrazione in uscita sconosciuta$") as raised:
        DeliverOutboxMessageUseCase(FakeMessengerAdapter()).execute(message)

    assert raised.value.permanent
    assert raised.value.details == {"integration": "posta"}


def test_a_message_without_its_chat_fails_for_good_and_is_never_retried(box: Outbox) -> None:
    box.outbox.enqueue(OutboxMessage(OutboxMessageId.new(), ANNA, CHAT_MESSAGE, {"text": "senza chat"}))

    box.process()
    box.outbox.let_backoff_pass()

    [message] = box.outbox.messages
    assert box.outbox.in_state(OutboxState.FAILED) == [message]
    assert box.outbox.attempts[message.id] == 1
    assert box.messenger.sent == []


def test_a_malformed_message_is_a_permanent_error_of_the_delivery() -> None:
    message = OutboxMessage(OutboxMessageId.new(), ANNA, CHAT_MESSAGE, {"chat_id": CHAT.value})

    with pytest.raises(InvalidOutboxMessageError):
        DeliverOutboxMessageUseCase(FakeMessengerAdapter()).execute(message)
