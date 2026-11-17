from autotrading.application.notifications.ports import NotificationEmailRepositoryPort


class RemoveNotificationEmailUseCase:
    """Removes the address of the notifications by email: the notifications stop going there, the flows go on
    (R3.5.2).
    """

    def __init__(self, emails: NotificationEmailRepositoryPort) -> None:
        self._emails = emails

    def execute(self) -> None:
        self._emails.remove()
