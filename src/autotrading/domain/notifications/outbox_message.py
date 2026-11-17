from collections.abc import Mapping
from dataclasses import dataclass

from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.email_address import EmailAddress
from autotrading.domain.notifications.errors import InvalidOutboxMessageError
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.notifications.notification_email import NotificationEmail
from autotrading.domain.notifications.outbox_message_id import OutboxMessageId
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.tenant_owned import TenantOwned

# The integration of the messages to the chat linked to a tenant; every next integration names its own.
CHAT_MESSAGE = "chat_message"
CHAT = "chat_id"
TEXT = "text"
# The integration of the emails to the address of the notifications of a tenant (R3.5.2).
EMAIL_MESSAGE = "email_message"
TO = "to"
SUBJECT = "subject"

type OutboxPayload = Mapping[str, str | int]


@dataclass(frozen=True, slots=True)
class ChatMessage:
    chat_id: ChatId
    text: str


@dataclass(frozen=True, slots=True)
class EmailMessage:
    address: EmailAddress
    subject: str
    text: str


@dataclass(frozen=True, slots=True)
class OutboxMessage(TenantOwned):
    """A message to an external system, kept with its tenant until it is delivered (ADR
    outbox-delle-integrazioni-esterne-con-procrastinate).
    """

    id: OutboxMessageId
    tenant_id: TenantId
    integration: str
    payload: OutboxPayload

    @classmethod
    def to_chat(cls, chat: LinkedChat, text: str) -> OutboxMessage:
        return cls(OutboxMessageId.new(), chat.tenant_id, CHAT_MESSAGE, {CHAT: chat.chat_id.value, TEXT: text})

    def chat_message(self) -> ChatMessage:
        chat_id, text = self.payload.get(CHAT), self.payload.get(TEXT)
        if not isinstance(chat_id, int) or not isinstance(text, str):
            raise InvalidOutboxMessageError
        return ChatMessage(ChatId(chat_id), text)

    @classmethod
    def to_email(cls, email: NotificationEmail, subject: str, text: str) -> OutboxMessage:
        payload = {TO: email.address.value, SUBJECT: subject, TEXT: text}
        return cls(OutboxMessageId.new(), email.tenant_id, EMAIL_MESSAGE, payload)

    def email_message(self) -> EmailMessage:
        address, subject, text = self.payload.get(TO), self.payload.get(SUBJECT), self.payload.get(TEXT)
        if not isinstance(address, str) or not isinstance(subject, str) or not isinstance(text, str):
            raise InvalidOutboxMessageError
        if not EmailAddress.accepts(address):
            raise InvalidOutboxMessageError
        return EmailMessage(EmailAddress(address), subject, text)
