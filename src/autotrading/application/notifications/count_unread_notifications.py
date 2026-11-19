from autotrading.application.notifications.ports import NotificationInboxPort


class CountUnreadNotificationsUseCase:
    """How many notifications of the tenant are unread: the number of the bell (R6.2.1)."""

    def __init__(self, inbox: NotificationInboxPort) -> None:
        self._inbox = inbox

    def execute(self) -> int:
        return self._inbox.unread_count()
