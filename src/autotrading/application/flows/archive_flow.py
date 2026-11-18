import logging
from dataclasses import dataclass

from autotrading.application.flows.ports import AlertResolutionPort, FlowRepositoryPort
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId

operations = logging.getLogger("autotrading.flows")


@dataclass(frozen=True, slots=True)
class ArchiveFlowCommand:
    flow_id: FlowId


class ArchiveFlowUseCase:
    """Archives a stopped flow for good: its capital and its assets return to its account (R1.1.6); the alert of a pause
    still open resolves (R6.2.3).
    """

    def __init__(self, flows: FlowRepositoryPort, alerts: AlertResolutionPort) -> None:
        self._flows = flows
        self._alerts = alerts

    def execute(self, command: ArchiveFlowCommand) -> Flow:
        flow = self._flows.get(command.flow_id).archived()
        self._flows.change_status(flow)
        self._alerts.resolve_flow_pause(flow.id)
        operations.info("flusso archiviato", extra={"flow_id": str(flow.id.value)})
        return flow
