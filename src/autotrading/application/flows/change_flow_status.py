import logging
from dataclasses import dataclass

from autotrading.application.flows.ports import FlowRepositoryPort
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_command import FlowCommand
from autotrading.domain.flows.flow_id import FlowId

operations = logging.getLogger("autotrading.flows")


@dataclass(frozen=True, slots=True)
class ChangeFlowStatusCommand:
    flow_id: FlowId
    command: FlowCommand


class ChangeFlowStatusUseCase:
    """Starts, pauses or resumes a flow when its status admits the command (R1.1.4)."""

    def __init__(self, flows: FlowRepositoryPort) -> None:
        self._flows = flows

    def execute(self, command: ChangeFlowStatusCommand) -> Flow:
        flow = self._flows.get(command.flow_id).after(command.command)
        self._flows.change_status(flow)
        operations.info("stato del flusso cambiato", extra={"flow_id": str(flow.id.value), "status": flow.status.name})
        return flow
