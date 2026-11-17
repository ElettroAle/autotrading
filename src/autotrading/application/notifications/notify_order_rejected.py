from uuid import UUID

from autotrading.application.notifications.notify_flow_event import NotifyFlowEventUseCase
from autotrading.domain.notifications.notification import Notification


class NotifyOrderRejectedUseCase:
    """Tells the user the exchange refused an order of a flow, with its message (R1.8.2)."""

    def __init__(self, notifier: NotifyFlowEventUseCase) -> None:
        self._notifier = notifier

    def execute(self, flow_id: UUID, flow_name: str, message: str) -> None:
        self._notifier.execute(Notification.order_rejected(flow_id, flow_name, message))
