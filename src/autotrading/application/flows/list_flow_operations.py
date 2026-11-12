from dataclasses import dataclass
from uuid import UUID

from autotrading.application.flows.ports import FlowOperationsPort, FlowRepositoryPort
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.operations import OperationsPage, OperationsQuery


@dataclass(frozen=True, slots=True)
class ListFlowOperationsCommand:
    flow_id: UUID
    query: OperationsQuery


class ListFlowOperationsUseCase:
    """The executions and funding payments of a flow of the tenant, newest first, a page at a time (ADR 0072)."""

    def __init__(self, flows: FlowRepositoryPort, operations: FlowOperationsPort) -> None:
        self._flows = flows
        self._operations = operations

    def execute(self, command: ListFlowOperationsCommand) -> OperationsPage:
        flow = self._flows.get(FlowId(command.flow_id))
        return self._operations.of_flow(flow.id, command.query)
