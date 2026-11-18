from uuid import UUID

from autotrading.application.notifications.ports import AlertRepositoryPort, NotifierPort
from autotrading.domain.notifications.alert import AlertCause
from autotrading.domain.notifications.notification import Notification


class NotifyUnattributableFillUseCase:
    """Opens the alert of an execution no flow ordered, then tells the user by the name of the account (R1.6.2,
    R6.2.3).
    """

    def __init__(self, notifier: NotifierPort, alerts: AlertRepositoryPort) -> None:
        self._notifier = notifier
        self._alerts = alerts

    def execute(self, account_id: UUID, account_name: str, asset: str) -> None:
        alert_id = self._alerts.open(AlertCause.unattributable_fill(account_id, account_name, asset))
        self._notifier.execute(Notification.unattributable_fill(alert_id.value, account_name, asset))
