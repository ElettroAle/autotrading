from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.email_address import EmailAddress
from autotrading.domain.notifications.errors import InvalidOutboxMessageError
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.notifications.notification_email import NotificationEmail
from autotrading.domain.notifications.notification_link import NotificationLink
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
# The pages of the dashboard a notification leads to (ADR destinazioni-delle-notifiche-nella-dashboard); a message
# queued before them has none.
LINKS = "links"
LABEL = "label"
URL = "url"

type OutboxPayload = Mapping[str, str | int | Sequence[Mapping[str, str]]]
type Links = tuple[NotificationLink, ...]


@dataclass(frozen=True, slots=True)
class ChatMessage:
    chat_id: ChatId
    text: str
    links: Links = ()


@dataclass(frozen=True, slots=True)
class EmailMessage:
    address: EmailAddress
    subject: str
    text: str
    links: Links = ()

    @property
    def body(self) -> str:
        """The text, then a blank line and a line for each link: plain text reads them at the bottom (R3.5.6)."""
        if not self.links:
            return self.text
        return "\n".join((self.text, "", *(f"{link.label}: {link.url}" for link in self.links)))


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
    def to_chat(cls, chat: LinkedChat, text: str, *, links: Links = ()) -> OutboxMessage:
        payload: OutboxPayload = {CHAT: chat.chat_id.value, TEXT: text, **_payload_of(links)}
        return cls(OutboxMessageId.new(), chat.tenant_id, CHAT_MESSAGE, payload)

    def chat_message(self) -> ChatMessage:
        chat_id, text = self.payload.get(CHAT), self.payload.get(TEXT)
        if not isinstance(chat_id, int) or not isinstance(text, str):
            raise InvalidOutboxMessageError
        return ChatMessage(ChatId(chat_id), text, self._links())

    @classmethod
    def to_email(cls, email: NotificationEmail, subject: str, text: str, *, links: Links = ()) -> OutboxMessage:
        payload: OutboxPayload = {TO: email.address.value, SUBJECT: subject, TEXT: text, **_payload_of(links)}
        return cls(OutboxMessageId.new(), email.tenant_id, EMAIL_MESSAGE, payload)

    def email_message(self) -> EmailMessage:
        address, subject, text = self.payload.get(TO), self.payload.get(SUBJECT), self.payload.get(TEXT)
        if not isinstance(address, str) or not isinstance(subject, str) or not isinstance(text, str):
            raise InvalidOutboxMessageError
        if not EmailAddress.accepts(address):
            raise InvalidOutboxMessageError
        return EmailMessage(EmailAddress(address), subject, text, self._links())

    def _links(self) -> Links:
        links = self.payload.get(LINKS, ())
        if isinstance(links, str | int):
            raise InvalidOutboxMessageError
        return tuple(_link_of(link) for link in links)


def _payload_of(links: Links) -> dict[str, list[dict[str, str]]]:
    """The links of the message, only when it has some: a message without links keeps the form it always had."""
    if not links:
        return {}
    return {LINKS: [{LABEL: link.label, URL: link.url} for link in links]}


def _link_of(link: object) -> NotificationLink:
    label, url = (link.get(LABEL), link.get(URL)) if isinstance(link, Mapping) else (None, None)
    if not isinstance(label, str) or not isinstance(url, str):
        raise InvalidOutboxMessageError
    return NotificationLink(label, url)
