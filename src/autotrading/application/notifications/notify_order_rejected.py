from autotrading.application.notifications.ports import NotifierPort
from autotrading.domain.notifications.notification import Notification


class NotifyOrderRejectedUseCase:
    """Tells the user the exchange refused an order of a flow, with its message (R1.8.2)."""

    def __init__(self, notifier: NotifierPort) -> None:
        self._notifier = notifier

    def execute(self, flow_name: str, message: str) -> None:
        self._notifier.execute(Notification.order_rejected(flow_name, message))
