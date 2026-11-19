from dataclasses import dataclass

from autotrading.application.notifications.ports import NotificationInboxPort
from autotrading.domain.notifications.inbox_page import InboxCursor, InboxPage


@dataclass(frozen=True, slots=True)
class ListInboxNotificationsCommand:
    after: InboxCursor | None = None


class ListInboxNotificationsUseCase:
    """The notifications of the bell of the tenant, newest first, by pages (R6.2.1, ADR 0074)."""

    def __init__(self, inbox: NotificationInboxPort) -> None:
        self._inbox = inbox

    def execute(self, command: ListInboxNotificationsCommand) -> InboxPage:
        return self._inbox.list(command.after)
