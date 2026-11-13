import logging
from dataclasses import dataclass

from autotrading.application.flows.ports import FlowRepositoryPort, RunningVerificationsPort
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_command import FlowCommand
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus

operations = logging.getLogger("autotrading.flows")


@dataclass(frozen=True, slots=True)
class ChangeFlowStatusCommand:
    flow_id: FlowId
    command: FlowCommand


class ChangeFlowStatusUseCase:
    """Starts, pauses or resumes a flow when its status admits the command (R1.1.4).

    A flow that would trade does not start or resume while the procedure of verification runs on one of its assets:
    the assets stay free of procedures until the new status is recorded (R0.4.1, ADR 0079).
    """

    def __init__(self, flows: FlowRepositoryPort, verifications: RunningVerificationsPort) -> None:
        self._flows = flows
        self._verifications = verifications

    def execute(self, command: ChangeFlowStatusCommand) -> Flow:
        flow = self._flows.get(command.flow_id).after(command.command)
        self._record_status(flow)
        operations.info("stato del flusso cambiato", extra={"flow_id": str(flow.id.value), "status": flow.status.name})
        return flow

    def _record_status(self, flow: Flow) -> None:
        if flow.status is not FlowStatus.ACTIVE:
            self._flows.change_status(flow)
            return
        with self._verifications.kept_free(flow.account_id, flow.configuration.assets):
            self._flows.change_status(flow)
