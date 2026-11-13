from autotrading.application.notifications.ports import NotifierPort
from autotrading.domain.notifications.notification import Notification


class NotifyUnattributablePositionUseCase:
    """Tells the user the account shows a position no flow opened, by the name of the account (R1.6.2)."""

    def __init__(self, notifier: NotifierPort) -> None:
        self._notifier = notifier

    def execute(self, account_name: str, asset: str) -> None:
        self._notifier.execute(Notification.unattributable_position(account_name, asset))
