from dataclasses import dataclass

from autotrading.application.notifications.ports import NotificationInboxPort
from autotrading.domain.notifications.inbox_notification import InboxNotificationId


@dataclass(frozen=True, slots=True)
class MarkNotificationReadCommand:
    notification_id: InboxNotificationId


class MarkNotificationReadUseCase:
    """The user reads one notification of the bell, choosing it or marking it (R6.2.1)."""

    def __init__(self, inbox: NotificationInboxPort) -> None:
        self._inbox = inbox

    def execute(self, command: MarkNotificationReadCommand) -> None:
        self._inbox.mark_read(command.notification_id)
