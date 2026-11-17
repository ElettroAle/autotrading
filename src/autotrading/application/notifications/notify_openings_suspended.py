from autotrading.application.notifications.notify_flow_event import NotifyFlowEventUseCase
from autotrading.domain.notifications.notification import Notification


class NotifyOpeningsSuspendedUseCase:
    """Tells the user the openings of a flow are suspended for maximum loss, with the threshold passed (R3.2.2)."""

    def __init__(self, notifier: NotifyFlowEventUseCase) -> None:
        self._notifier = notifier

    def execute(self, flow_name: str, reason: str) -> None:
        self._notifier.execute(Notification.openings_suspended(flow_name, reason))
