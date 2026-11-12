from dataclasses import dataclass

from autotrading.application.flows.ports import FlowRepositoryPort
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_id import FlowId


@dataclass(frozen=True, slots=True)
class GetFlowVersionCommand:
    flow_id: FlowId
    version: int


class GetFlowVersionUseCase:
    """Any configuration version of a flow, the previous ones included (R1.1.3)."""

    def __init__(self, flows: FlowRepositoryPort) -> None:
        self._flows = flows

    def execute(self, command: GetFlowVersionCommand) -> FlowConfiguration:
        return self._flows.version(command.flow_id, command.version)
