from dataclasses import dataclass

from autotrading.application.flows.ports import FlowRepositoryPort
from autotrading.domain.flows.configuration_difference import ConfigurationDifference, differences
from autotrading.domain.flows.flow_id import FlowId


@dataclass(frozen=True, slots=True)
class CompareFlowVersionsCommand:
    flow_id: FlowId
    first: int
    second: int


class CompareFlowVersionsUseCase:
    """What changed from one configuration version of a flow to another (R1.1.3)."""

    def __init__(self, flows: FlowRepositoryPort) -> None:
        self._flows = flows

    def execute(self, command: CompareFlowVersionsCommand) -> tuple[ConfigurationDifference, ...]:
        first = self._flows.version(command.flow_id, command.first)
        second = self._flows.version(command.flow_id, command.second)
        return differences(first, second)
