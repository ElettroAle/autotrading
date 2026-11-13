from autotrading.application.notifications.ports import NotifierPort
from autotrading.domain.notifications.notification import Notification


class NotifyCycleFailedUseCase:
    """Tells the user a cycle of a flow failed, with the message of its error (R1.8.2)."""

    def __init__(self, notifier: NotifierPort) -> None:
        self._notifier = notifier

    def execute(self, flow_name: str, reason: str) -> None:
        self._notifier.execute(Notification.cycle_failed(flow_name, reason))
