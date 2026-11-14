from dataclasses import dataclass

from autotrading.application.flows.ports import FlowRepositoryPort
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.flow_strategy import FlowStrategy


@dataclass(frozen=True, slots=True)
class ExportFlowStrategyCommand:
    flow_id: FlowId


@dataclass(frozen=True, slots=True)
class ExportedFlowStrategy:
    """The strategy of a flow with the name of the flow, which names the file (ADR 0140)."""

    flow_name: FlowName
    strategy: FlowStrategy


class ExportFlowStrategyUseCase:
    """The strategy of the version in force of a flow of the tenant, to save it or use it again (R2.5.2, ADR 0140).

    Any flow exports, an archived one too: the strategy outlives the flow, which can be created again from it.
    """

    def __init__(self, flows: FlowRepositoryPort) -> None:
        self._flows = flows

    def execute(self, command: ExportFlowStrategyCommand) -> ExportedFlowStrategy:
        flow = self._flows.get(command.flow_id)
        return ExportedFlowStrategy(flow.name, FlowStrategy.of(flow.configuration))
