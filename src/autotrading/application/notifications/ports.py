from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.email_address import EmailAddress
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.notifications.notification import Notification
from autotrading.domain.notifications.notification_email import NotificationEmail
from autotrading.domain.notifications.outbox_message import OutboxMessage
from autotrading.domain.notifications.pending_link import PendingLink
from autotrading.domain.tenancy.tenant_id import TenantId


class LinkCodeRepositoryPort(Protocol):
    """Bound to the tenant of the request: it never sees the codes of another tenant."""

    def add(self, link: PendingLink) -> None: ...

    def get(self, digest: bytes) -> PendingLink | None: ...

    def use(self, digest: bytes) -> bool:
        """Marks the code used; False when it was already used, so two chats can never both redeem it."""
        ...


class LinkCodeLookupPort(Protocol):
    """The only lookup made before the tenant is known: who asked for the code with this digest (ADR 0035)."""

    def tenant_of(self, digest: bytes) -> TenantId | None: ...


class LinkedChatRepositoryPort(Protocol):
    """Bound to the tenant of the request."""

    def get(self) -> LinkedChat | None: ...

    def link(self, chat: LinkedChat) -> None:
        """Links the chat, replacing the one linked before (R1.8.1)."""
        ...

    def unlink(self) -> None:
        """Raises ChatNotLinkedError when the tenant has no linked chat."""
        ...


class LinkedChatLookupPort(Protocol):
    """The only lookup made before the tenant is known from a chat: the tenants it is linked to (ADR 0081)."""

    def tenants_of(self, chat_id: ChatId) -> tuple[TenantId, ...]: ...


class MessengerPort(Protocol):
    def send(self, chat_id: ChatId, text: str) -> None:
        """Raises MessageNotDeliveredError when Telegram does not take the message."""
        ...


class NotificationEmailRepositoryPort(Protocol):
    """Bound to the tenant of the request: the only address its notifications go to by email (R3.5.2)."""

    def get(self) -> NotificationEmail | None: ...

    def set(self, email: NotificationEmail) -> None:
        """Keeps the address, replacing the one kept before."""
        ...

    def remove(self) -> None:
        """Forgets the address; nothing to forget is no error."""
        ...


class MailerPort(Protocol):
    def send(self, address: EmailAddress, subject: str, text: str) -> None:
        """Raises MessageNotDeliveredError when the mail service does not take the email."""
        ...


class MailServicePort(Protocol):
    def is_configured(self) -> bool:
        """Whether the installation has a mail service: without one no email leaves (R3.5.2)."""
        ...


@dataclass(frozen=True, slots=True)
class BotMessage:
    chat_id: ChatId
    text: str


class BotInboxPort(Protocol):
    def receive(self) -> Sequence[BotMessage]:
        """The messages sent to the bot since the last call, waiting for some; raises BotUnreachableError."""
        ...


@dataclass(frozen=True, slots=True)
class LinkStores:
    """The stores of one tenant that redeeming a code changes."""

    codes: LinkCodeRepositoryPort
    chats: LinkedChatRepositoryPort


class NotifierPort(Protocol):
    def execute(self, notification: Notification) -> None:
        """Delivers the notification to the channels of the tenant; a delivery that fails is recorded, never raised."""
        ...


class BotStartLinkPort(Protocol):
    def start_link(self, code: str) -> str | None:
        """The link that opens the chat with the platform bot and sends it the code; none without an active bot."""
        ...


class OutboxPort(Protocol):
    """The messages to external systems, kept with their tenant until delivered (ADR
    outbox-delle-integrazioni-esterne-con-procrastinate).
    """

    def enqueue(self, message: OutboxMessage) -> None:
        """Keeps the message and queues it in one transaction; raises OutboxUnavailableError when it cannot."""
        ...

    def process(self, deliver: Callable[[OutboxMessage], None]) -> None:
        """Hands every queued message to deliver for as long as the service runs.

        A transient error of deliver is retried with exponential backoff up to the last attempt, a permanent one
        marks the message failed at once; raises OutboxUnavailableError when the queue cannot be served.
        """
        ...
