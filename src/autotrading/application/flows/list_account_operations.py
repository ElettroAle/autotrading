from dataclasses import dataclass
from uuid import UUID

from autotrading.application.flows.ports import FlowOperationsPort
from autotrading.domain.flows.operations import OperationsPage, OperationsQuery


@dataclass(frozen=True, slots=True)
class ListAccountOperationsCommand:
    account_id: UUID
    query: OperationsQuery


class ListAccountOperationsUseCase:
    """The executions and funding payments of an account of the tenant that belong to no flow (ADR 0074)."""

    def __init__(self, operations: FlowOperationsPort) -> None:
        self._operations = operations

    def execute(self, command: ListAccountOperationsCommand) -> OperationsPage:
        return self._operations.unattributed_of_account(command.account_id, command.query)
