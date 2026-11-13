from collections.abc import Iterator
from dataclasses import dataclass
from uuid import UUID

from autotrading.application.flows.ports import FlowOperationsPort, FlowRepositoryPort
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.operations import FlowOperations, Operation, OperationsQuery


@dataclass(frozen=True, slots=True)
class ExportFlowOperationsCommand:
    flow_id: UUID
    query: OperationsQuery


class ExportFlowOperationsUseCase:
    """Every row of a flow of the tenant that the filter admits, oldest first, read as it is consumed (ADR 0080).

    The flow is looked up before the rows are returned: an unknown flow is refused before anything is sent.
    """

    def __init__(self, flows: FlowRepositoryPort, operations: FlowOperationsPort) -> None:
        self._flows = flows
        self._operations = operations

    def execute(self, command: ExportFlowOperationsCommand) -> Iterator[Operation]:
        flow = self._flows.get(FlowId(command.flow_id))
        return self._operations.export(FlowOperations(flow.id), command.query)
