"""Fake of the bell of the tenants: every notification kept with its tenant, forgotten after the retention, like the
database does."""

from collections.abc import Callable
from datetime import UTC, datetime

from autotrading.application.notifications.errors import (
    InboxNotificationNotFoundError,
    NotificationInboxUnavailableError,
)
from autotrading.domain.notifications.inbox_notification import InboxNotification, InboxNotificationId
from autotrading.domain.notifications.inbox_page import INBOX_PAGE_SIZE, InboxCursor, InboxPage
from autotrading.domain.notifications.notification import Notification
from autotrading.domain.tenancy.tenant_id import TenantId

type InboxStore = dict[TenantId, list[InboxNotification]]

START = datetime(2026, 11, 19, 9, 0, tzinfo=UTC)


class InMemoryNotificationInboxAdapter:
    """Bound to a tenant, like the SQLAlchemy adapter under row level security; a notification is read at the instant
    of the clock, as the database reads it at its own. Unreachable, it keeps nothing, as a database that is down."""

    def __init__(self, store: InboxStore, tenant_id: TenantId, clock: Callable[[], datetime] = lambda: START) -> None:
        self.reachable = True
        self._store = store
        self._tenant_id = tenant_id
        self._clock = clock

    @property
    def notifications(self) -> list[InboxNotification]:
        return self._store.setdefault(self._tenant_id, [])

    def add(self, notification: Notification, at: datetime) -> None:
        if not self.reachable:
            raise NotificationInboxUnavailableError
        kept = [each for each in self.notifications if not each.forgotten_at(at)]
        self._store[self._tenant_id] = [*kept, InboxNotification.of(notification, at)]

    def list(self, cursor: InboxCursor | None) -> InboxPage:
        newest_first = sorted(self.notifications, key=InboxCursor.of, reverse=True)
        after = [each for each in newest_first if cursor is None or cursor.admits(each)]
        return InboxPage.of(after[: INBOX_PAGE_SIZE + 1], INBOX_PAGE_SIZE)

    def unread_count(self) -> int:
        return sum(1 for each in self.notifications if not each.is_read)

    def mark_read(self, notification_id: InboxNotificationId) -> None:
        if all(each.id != notification_id for each in self.notifications):
            raise InboxNotificationNotFoundError
        now = self._clock()
        self._store[self._tenant_id] = [
            each.read(now) if each.id == notification_id else each for each in self.notifications
        ]

    def mark_all_read(self) -> None:
        now = self._clock()
        self._store[self._tenant_id] = [each.read(now) for each in self.notifications]
