from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, time
from typing import Protocol
from uuid import UUID

from autotrading.domain.notifications.alert import Alert, AlertCause, AlertId, AlertKind
from autotrading.domain.notifications.alert_page import AlertCursor, AlertFilter, AlertPage
from autotrading.domain.notifications.channel_preferences import ChannelPreferences
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.expiring_key import ExpiringKey, KeyExpiryNotice
from autotrading.domain.notifications.flow_status import FlowStatusFigures
from autotrading.domain.notifications.inbox_notification import InboxNotificationId
from autotrading.domain.notifications.inbox_page import InboxCursor, InboxPage
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.notifications.mail_server import MailServer
from autotrading.domain.notifications.notification import Notification
from autotrading.domain.notifications.notification_email import NotificationEmail
from autotrading.domain.notifications.notification_link import NotificationLink
from autotrading.domain.notifications.notification_target import NotificationTarget
from autotrading.domain.notifications.outbox_message import EmailMessage, OutboxMessage
from autotrading.domain.notifications.pending_link import PendingLink
from autotrading.domain.notifications.sealed_mail_password import SealedMailPassword
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
    def send(self, chat_id: ChatId, text: str, links: Sequence[NotificationLink] = ()) -> None:
        """Sends the text with a button under it for each link (ADR link-nei-messaggi-telegram-ed-email).

        Raises MessageNotDeliveredError when Telegram does not take the message.
        """
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
    def send(self, server: MailServer, password: str, email: EmailMessage) -> None:
        """Sends the email, its links at the bottom of the text, from the mail server of the tenant, logged in with its
        opened password (ADR invio-dal-server-di-posta-del-tenant, ADR link-nei-messaggi-telegram-ed-email).

        Raises MailServerRefusedLoginError when the server refuses user and password, EmailNotDeliveredError when it
        does not take the email for any other reason.
        """
        ...


class MailServerRepositoryPort(Protocol):
    """Bound to the tenant of the request: the only mail server its emails leave from (R3.5.5)."""

    def get(self) -> MailServer | None: ...

    def save(self, server: MailServer) -> None:
        """Keeps the server, replacing the one kept before."""
        ...

    def remove(self) -> None:
        """Forgets the server; nothing to forget is no error."""
        ...


class MailPasswordSealerPort(Protocol):
    """Bound to the tenant of the request: seals the password of its mail server, which only the worker opens (ADR
    server-di-posta-per-tenant)."""

    def seal(self, password: str) -> SealedMailPassword: ...


class MailPasswordOpenerPort(Protocol):
    """Bound to the tenant of the request, only in the worker: opens the password of its mail server to send."""

    def open(self, sealed: SealedMailPassword) -> str:
        """Raises MailPasswordNotOpenedError when the sealed text is not a password sealed for this tenant."""
        ...


@dataclass(frozen=True, slots=True)
class MailServerAccess:
    """What sends from the mail server of one tenant: the server it saved and the opener of its password."""

    servers: MailServerRepositoryPort
    opener: MailPasswordOpenerPort


class EmailTestPort(Protocol):
    """Bound to the tenant of the request: sends the test email now, from the mail server of the tenant (ADR
    invio-dal-server-di-posta-del-tenant).

    Only the worker opens the password: in the API it is the client that asks the worker to run SendTestEmailUseCase.
    """

    def send_test(self) -> None:
        """Raises MailServerNotConfiguredError, NoNotificationEmailToTestError, MailServerRefusedLoginError,
        MailPasswordNotOpenedError, or EmailNotDeliveredError."""
        ...


class ChannelPreferencesRepositoryPort(Protocol):
    """Bound to the tenant of the request: the channel of every type of event and the exceptions of the flows
    (R3.5.3).
    """

    def get(self) -> ChannelPreferences:
        """The preferences of the tenant; those of a tenant who never chose when nothing is kept."""
        ...

    def save(self, preferences: ChannelPreferences) -> None:
        """Keeps the preferences, replacing those kept before; raises NotifiedFlowNotFoundError when an exception
        names a flow the tenant lacks."""
        ...


@dataclass(frozen=True, slots=True)
class NotifiedFlow:
    flow_id: UUID
    name: str


class NotifiedFlowsPort(Protocol):
    """Bound to the tenant of the request: the flows a notification may name, by the name it names them with."""

    def list(self) -> Sequence[NotifiedFlow]:
        """The flows of the tenant not archived, whose names are unique among them (R1.1.1), by name."""
        ...


class NotificationLinkPort(Protocol):
    def link(self, target: NotificationTarget) -> NotificationLink | None:
        """The page of the dashboard the target leads to; none when the installation names no dashboard, and the
        notification leaves without it (ADR destinazioni-delle-notifiche-nella-dashboard).
        """
        ...


@dataclass(frozen=True, slots=True)
class NotificationRoutes:
    """Where a notification goes: the channels the tenant chose for its event, or for the exception of its flow, and
    the pages of the dashboard it leads to.
    """

    preferences: ChannelPreferencesRepositoryPort
    links: NotificationLinkPort


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


class FlowStatusPort(Protocol):
    """Bound to the tenant of the request: the state of a flow as its last cycle recorded it (ADR
    stato-del-flusso-in-ogni-notifica).
    """

    def status_of(self, flow_name: str) -> FlowStatusFigures | None:
        """The figures of the flow not archived with that name, none without one; raises FlowStatusUnavailableError."""
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


class AlertRepositoryPort(Protocol):
    """Bound to the tenant of the request: the alerts of its accounts, flows and keys, open and resolved (R6.2.3, ADR
    avvisi-nel-contesto-delle-notifiche).
    """

    def open(self, cause: AlertCause) -> AlertId:
        """Opens the alert of the cause, unless one with the same key is open, and gives the id of the open one; forgets
        the alerts of the tenant resolved more than RESOLVED_ALERT_RETENTION ago."""
        ...

    def get(self, alert_id: AlertId) -> Alert:
        """Raises AlertNotFoundError for an alert that does not exist and for one of another tenant."""
        ...

    def resolve(self, alert_id: AlertId) -> None:
        """Resolves the alert now; a resolved alert keeps the instant it was resolved."""
        ...

    def list(self, criteria: AlertFilter, cursor: AlertCursor | None) -> AlertPage:
        """The alerts the filter admits, newest first, from the cursor, with how many it admits in all (ADR 0074)."""
        ...

    def open_count(self) -> int: ...

    def resolve_all_but(self, kind: AlertKind, kept: frozenset[UUID]) -> None:
        """Resolves the open alerts of the kind whose resource is not among the kept ones (R6.2.2)."""
        ...


class ExpiringKeysPort(Protocol):
    """Bound to the tenant: every key of its accounts and providers that has an expiry, with the names of the flows not
    archived that use it (R6.2.2, ADR controllo-giornaliero-delle-scadenze)."""

    def expiring_keys(self) -> tuple[ExpiringKey, ...]: ...


class KeyExpiryNoticeRepositoryPort(Protocol):
    """Bound to the tenant: the thresholds already told for each expiry of its keys (R6.2.2)."""

    def record(self, notice: KeyExpiryNotice) -> bool:
        """Records the notice; False when it was already recorded, so a threshold is told once."""
        ...


class KeyExpiryTenantsPort(Protocol):
    """Every tenant of the platform, for the daily check of the expiries of their keys (R6.2.2)."""

    def tenant_ids(self) -> tuple[TenantId, ...]: ...


class DailyCheckSchedulerPort(Protocol):
    def keep_daily(self, name: str, at: time, run: Callable[[], None]) -> None:
        """Runs the check once at once, then every day at the instant, while the worker is up; an error of the project
        it raises is recorded, never raised (ADR controllo-giornaliero-delle-scadenze)."""
        ...


class NotificationInboxPort(Protocol):
    """Bound to the tenant of the request: every notification the platform generated for it, read or not, for the bell
    (R6.2.1, ADR notifiche-nell-app-salvate-per-tenant). Not a channel: it keeps the notifications, it delivers nothing.
    """

    def add(self, notification: Notification, at: datetime) -> None:
        """Keeps the notification generated at the instant, unread, and forgets those older than INBOX_RETENTION;
        raises NotificationInboxUnavailableError when it cannot."""
        ...

    def list(self, cursor: InboxCursor | None) -> InboxPage:
        """INBOX_PAGE_SIZE notifications, newest first, from the cursor (ADR 0074)."""
        ...

    def unread_count(self) -> int: ...

    def mark_read(self, notification_id: InboxNotificationId) -> None:
        """Marks the notification read; one read before keeps the instant it was first read. Raises
        InboxNotificationNotFoundError for a notification that does not exist and for one of another tenant."""
        ...

    def mark_all_read(self) -> None: ...


class ClockPort(Protocol):
    def now(self) -> datetime: ...


@dataclass(frozen=True, slots=True)
class NotificationInbox:
    """Where every notification of the tenant is kept for the bell, and the clock that dates it."""

    notifications: NotificationInboxPort
    clock: ClockPort
