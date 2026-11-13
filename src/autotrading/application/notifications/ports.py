from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.linked_chat import LinkedChat
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


class BotIdentityPort(Protocol):
    def username(self) -> str | None:
        """The username of the platform bot; none when no bot is active or it cannot be reached now."""
        ...
