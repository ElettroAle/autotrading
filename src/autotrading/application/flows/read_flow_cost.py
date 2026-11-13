from dataclasses import dataclass
from uuid import UUID

from autotrading.application.flows.errors import CycleFlowNotFoundError
from autotrading.application.flows.ports import CycleHistoryPort, FlowDirectoryPort
from autotrading.domain.flows.flow_cost import FlowCost


@dataclass(frozen=True, slots=True)
class ReadFlowCostCommand:
    flow_id: UUID


class ReadFlowCostUseCase:
    """What the model calls of a flow of the tenant cost since its start and per UTC day (R1.4.6)."""

    def __init__(self, flows: FlowDirectoryPort, history: CycleHistoryPort) -> None:
        self._flows = flows
        self._history = history

    def execute(self, command: ReadFlowCostCommand) -> FlowCost:
        if not self._flows.exists(command.flow_id):
            raise CycleFlowNotFoundError
        return FlowCost.of(self._history.costs(command.flow_id))
