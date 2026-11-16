from uuid import UUID

from autotrading.application.flows.ports import FlowRepositoryPort
from autotrading.domain.flows.flow_id import FlowId


class ReadFlowActivityUseCase:
    """Whether the flow runs cycles now: only an active flow does (R1.1.4-R1.1.6, Bug 373)."""

    def __init__(self, flows: FlowRepositoryPort) -> None:
        self._flows = flows

    def execute(self, flow_id: UUID) -> bool:
        return self._flows.get(FlowId(flow_id)).status.runs_cycles
