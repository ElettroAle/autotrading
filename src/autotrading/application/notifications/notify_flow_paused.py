from uuid import UUID

from autotrading.application.notifications.notify_flow_event import NotifyFlowEventUseCase
from autotrading.domain.notifications.notification import Notification


class NotifyFlowPausedUseCase:
    """Tells the user a flow paused on its own, with the reason (R1.2.4, R1.8.2)."""

    def __init__(self, notifier: NotifyFlowEventUseCase) -> None:
        self._notifier = notifier

    def execute(self, flow_id: UUID, flow_name: str, reason: str) -> None:
        self._notifier.execute(Notification.flow_paused(flow_id, flow_name, reason))
