from autotrading.application.notifications.ports import NotifierPort
from autotrading.domain.notifications.notification import Notification


class NotifyFlowPausedUseCase:
    """Tells the user a flow paused on its own, with the reason (R1.2.4, R1.8.2)."""

    def __init__(self, notifier: NotifierPort) -> None:
        self._notifier = notifier

    def execute(self, flow_name: str, reason: str) -> None:
        self._notifier.execute(Notification.flow_paused(flow_name, reason))
