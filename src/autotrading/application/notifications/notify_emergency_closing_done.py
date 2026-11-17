from collections.abc import Sequence

from autotrading.application.notifications.ports import NotifierPort
from autotrading.domain.notifications.notification import Notification


class NotifyEmergencyClosingDoneUseCase:
    """Tells the user an emergency closing was made, once, with the positions it closed and the flows left paused
    (R3.5.1).
    """

    def __init__(self, notifier: NotifierPort) -> None:
        self._notifier = notifier

    def execute(self, positions_closed: int, paused_flows: Sequence[str]) -> None:
        self._notifier.execute(Notification.emergency_closing_done(positions_closed, paused_flows))
