from uuid import UUID

from autotrading.application.notifications.notify_flow_event import NotifyFlowEventUseCase
from autotrading.domain.notifications.notification import Notification


class NotifyOpeningBlockedUseCase:
    """Tells the user the risk check blocked an opening of a flow, with its cause (R3.5.1)."""

    def __init__(self, notifier: NotifyFlowEventUseCase) -> None:
        self._notifier = notifier

    def execute(self, flow_id: UUID, flow_name: str, asset: str, cause: str) -> None:
        self._notifier.execute(Notification.opening_blocked(flow_id, flow_name, asset, cause))
