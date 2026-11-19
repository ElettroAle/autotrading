from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from autotrading.domain.notifications.inbox_notification import InboxNotification

# The bell shows the newest twenty and reads the next ones on request (ADR campanello-delle-notifiche-nella-dashboard).
INBOX_PAGE_SIZE = 20


@dataclass(frozen=True, slots=True, order=True)
class InboxCursor:
    """The place of a notification in the bell, newest first: its instant, then its id (ADR 0074)."""

    notified_at: datetime
    notification_id: UUID

    def admits(self, notification: InboxNotification) -> bool:
        """Whether the notification comes after this place, older than the one it marks."""
        return InboxCursor.of(notification) < self

    @classmethod
    def of(cls, notification: InboxNotification) -> InboxCursor:
        return cls(notification.notified_at, notification.id.value)


@dataclass(frozen=True, slots=True)
class InboxPage:
    """A page of the bell, newest first, and where the next page starts if there is one."""

    notifications: tuple[InboxNotification, ...]
    next: InboxCursor | None

    @classmethod
    def of(cls, newest_first: Sequence[InboxNotification], limit: int) -> InboxPage:
        """The page from up to one notification more than the limit: that extra one says another page follows."""
        page = tuple(newest_first[:limit])
        more = len(newest_first) > limit
        return cls(page, InboxCursor.of(page[-1]) if more and page else None)
