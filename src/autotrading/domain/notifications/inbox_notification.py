from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from autotrading.domain.notifications.errors import InvalidInboxNotificationError
from autotrading.domain.notifications.notification import Notification
from autotrading.domain.notifications.notification_target import NotificationTarget

# A notification of the bell older than this is forgotten (R6.2.1).
INBOX_RETENTION = timedelta(days=90)


@dataclass(frozen=True, slots=True)
class InboxNotificationId:
    value: UUID

    @classmethod
    def new(cls) -> InboxNotificationId:
        return cls(uuid4())


@dataclass(frozen=True, slots=True)
class InboxNotification:
    """A notification the platform generated for the tenant, as the bell keeps it: its icon, the flow or account and the
    event, its values, the pages it leads to, and when the user read it (R6.2.1, ADR
    notifiche-nell-app-salvate-per-tenant). Kept whatever its channels, read or not, for INBOX_RETENTION.
    """

    id: InboxNotificationId
    notified_at: datetime
    icon: str
    title: str
    text: str
    targets: tuple[NotificationTarget, ...]
    read_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.notified_at.tzinfo is None:
            raise InvalidInboxNotificationError

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    def read(self, at: datetime) -> InboxNotification:
        """The notification read at the instant; one read before keeps the instant it was first read."""
        if self.is_read:
            return self
        return replace(self, read_at=at)

    def forgotten_at(self, now: datetime) -> bool:
        return self.notified_at < now - INBOX_RETENTION

    @classmethod
    def of(cls, notification: Notification, at: datetime) -> InboxNotification:
        """The notification generated at the instant, unread."""
        return cls(
            InboxNotificationId.new(),
            at,
            notification.icon,
            notification.heading,
            "\n".join(notification.body_lines()),
            notification.targets,
        )
