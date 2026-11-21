from dataclasses import dataclass

from autotrading.application.flows.ports import FlowRepositoryPort
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId


@dataclass(frozen=True, slots=True)
class GetFlowCommand:
    flow_id: FlowId


class GetFlowUseCase:
    """One flow of the tenant with the configuration version in force, an archived one too, so its page opens in read
    only (Bug 690, ADR pagina-del-flusso-archiviato-in-sola-lettura); a flow of another tenant is not found (R0.1.3).
    """

    def __init__(self, flows: FlowRepositoryPort) -> None:
        self._flows = flows

    def execute(self, command: GetFlowCommand) -> Flow:
        return self._flows.get(command.flow_id)
