from autotrading.application.notifications.ports import NotifierPort
from autotrading.domain.notifications.notification import Notification


class NotifyOpeningBlockedUseCase:
    """Tells the user the risk check blocked an opening of a flow, with its cause (R3.5.1)."""

    def __init__(self, notifier: NotifierPort) -> None:
        self._notifier = notifier

    def execute(self, flow_name: str, asset: str, cause: str) -> None:
        self._notifier.execute(Notification.opening_blocked(flow_name, asset, cause))
