from autotrading.application.notifications.ports import NotifierPort
from autotrading.domain.notifications.notification import Notification


class NotifyOpeningsSuspendedUseCase:
    """Tells the user the openings of a flow are suspended for maximum loss, with the threshold passed (R3.2.2)."""

    def __init__(self, notifier: NotifierPort) -> None:
        self._notifier = notifier

    def execute(self, flow_name: str, reason: str) -> None:
        self._notifier.execute(Notification.openings_suspended(flow_name, reason))
