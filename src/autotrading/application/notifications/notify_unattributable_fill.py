from autotrading.application.notifications.ports import NotifierPort
from autotrading.domain.notifications.notification import Notification


class NotifyUnattributableFillUseCase:
    """Tells the user the account shows an execution no flow ordered, by the name of the account (R1.6.2)."""

    def __init__(self, notifier: NotifierPort) -> None:
        self._notifier = notifier

    def execute(self, account_name: str, asset: str) -> None:
        self._notifier.execute(Notification.unattributable_fill(account_name, asset))
