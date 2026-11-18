from uuid import UUID

from autotrading.application.notifications.notify_flow_event import NotifyFlowEventUseCase
from autotrading.application.notifications.ports import AlertRepositoryPort
from autotrading.domain.notifications.alert import AlertCause
from autotrading.domain.notifications.notification import Notification


class NotifyFlowPausedUseCase:
    """Opens the alert of a flow paused on its own, then tells the user, with the reason and the alert to open (R1.2.4,
    R1.8.2, R6.2.3, ADR 0092).
    """

    def __init__(self, notifier: NotifyFlowEventUseCase, alerts: AlertRepositoryPort) -> None:
        self._notifier = notifier
        self._alerts = alerts

    def execute(self, flow_id: UUID, flow_name: str, reason: str) -> None:
        alert_id = self._alerts.open(AlertCause.flow_paused(flow_id, flow_name, reason))
        self._notifier.execute(Notification.flow_paused(flow_id, flow_name, reason, alert_id.value))
