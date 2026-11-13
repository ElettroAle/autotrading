from autotrading.domain.notifications.notification import Notification


class FakeNotifierAdapter:
    """The notifications of the tenant as the tests see them: what reached the user, in order."""

    def __init__(self) -> None:
        self.notifications: list[Notification] = []

    def execute(self, notification: Notification) -> None:
        self.notifications.append(notification)
