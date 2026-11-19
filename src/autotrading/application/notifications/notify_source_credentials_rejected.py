from autotrading.application.notifications.ports import NotifierPort
from autotrading.domain.notifications.notification import Notification


class NotifySourceCredentialsRejectedUseCase:
    """Tells the tenant the provider of an adapter of a source refused its credentials (R4.1.2, ADR
    credenziali-degli-adapter-delle-fonti)."""

    def __init__(self, notifier: NotifierPort) -> None:
        self._notifier = notifier

    def execute(self, adapter: str) -> None:
        self._notifier.execute(Notification.source_credentials_rejected(adapter))
