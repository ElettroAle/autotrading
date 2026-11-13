from dataclasses import dataclass
from uuid import UUID

from autotrading.application.flows.ports import FlowOperationsPort, FlowRepositoryPort
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.operations import FlowOperations, OperationsQuery, OperationsReport


@dataclass(frozen=True, slots=True)
class ListFlowOperationsCommand:
    flow_id: UUID
    query: OperationsQuery


class ListFlowOperationsUseCase:
    """The executions and funding payments of a flow of the tenant, newest first, a page at a time, with the totals of
    the whole filter (ADR 0074, ADR 0080).
    """

    def __init__(self, flows: FlowRepositoryPort, operations: FlowOperationsPort) -> None:
        self._flows = flows
        self._operations = operations

    def execute(self, command: ListFlowOperationsCommand) -> OperationsReport:
        flow = self._flows.get(FlowId(command.flow_id))
        return self._operations.report(FlowOperations(flow.id), command.query)
