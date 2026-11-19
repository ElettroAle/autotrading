from autotrading.application.notifications.notify_source_credentials_rejected import (
    NotifySourceCredentialsRejectedUseCase,
)
from autotrading.domain.notifications.notification import Notification


class RecordingNotifier:
    def __init__(self) -> None:
        self.notifications: list[Notification] = []

    def execute(self, notification: Notification) -> None:
        self.notifications.append(notification)


def test_tells_the_tenant_the_provider_refused_the_credentials_of_the_adapter() -> None:
    notifier = RecordingNotifier()

    NotifySourceCredentialsRejectedUseCase(notifier).execute("LunarCrush")

    assert notifier.notifications == [Notification.source_credentials_rejected("LunarCrush")]
