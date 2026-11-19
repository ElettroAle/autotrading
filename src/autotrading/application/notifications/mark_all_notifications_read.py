from autotrading.application.notifications.ports import NotificationInboxPort


class MarkAllNotificationsReadUseCase:
    """The user marks every notification of the bell read at once (R6.2.1)."""

    def __init__(self, inbox: NotificationInboxPort) -> None:
        self._inbox = inbox

    def execute(self) -> None:
        self._inbox.mark_all_read()
