from uuid import UUID

from autotrading.application.flows.ports import CycleFailedNoticePort, FlowRepositoryPort
from autotrading.domain.flows.flow_id import FlowId


class NotifyCycleFailureUseCase:
    """Tells the user, by the name of the flow, that one of its cycles failed (R1.8.2)."""

    def __init__(self, flows: FlowRepositoryPort, notice: CycleFailedNoticePort) -> None:
        self._flows = flows
        self._notice = notice

    def execute(self, flow_id: UUID, reason: str) -> None:
        flow = self._flows.get(FlowId(flow_id))
        self._notice.execute(flow.name.value, reason)
