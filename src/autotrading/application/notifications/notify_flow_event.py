import logging

from autotrading.application.notifications.errors import FlowStatusUnavailableError
from autotrading.application.notifications.ports import FlowStatusPort, NotifierPort
from autotrading.domain.notifications.flow_status import FlowStatusLine
from autotrading.domain.notifications.notification import Notification

operations = logging.getLogger("autotrading.notifications")


class NotifyFlowEventUseCase:
    """Delivers a notification of a flow with the state of the flow at the bottom (ADR
    stato-del-flusso-in-ogni-notifica).

    The state is the one of the last cycle recorded, never read from the exchange: a notification does not slow the
    cycle down (R1.8.2). A state that cannot be read is recorded and the notification leaves without it.
    """

    def __init__(self, notifier: NotifierPort, flow_status: FlowStatusPort) -> None:
        self._notifier = notifier
        self._flow_status = flow_status

    def execute(self, notification: Notification) -> None:
        self._notifier.execute(self._with_flow_status(notification))

    def _with_flow_status(self, notification: Notification) -> Notification:
        flow = notification.flow
        if flow is None:
            return notification
        try:
            figures = self._flow_status.status_of(flow)
        except FlowStatusUnavailableError:
            operations.warning("stato del flusso non letto per la notifica", exc_info=True, extra={"flow": flow})
            return notification
        if figures is None:
            return notification
        return notification.with_flow_status(FlowStatusLine.of(figures))
