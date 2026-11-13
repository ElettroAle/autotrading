from collections.abc import Iterator
from dataclasses import dataclass
from uuid import UUID

from autotrading.application.flows.ports import FlowOperationsPort
from autotrading.domain.flows.operations import AccountOperations, AccountScope, Operation, OperationsQuery


@dataclass(frozen=True, slots=True)
class ExportAccountOperationsCommand:
    account_id: UUID
    query: OperationsQuery
    scope: AccountScope


class ExportAccountOperationsUseCase:
    """Every row of an account of the tenant that the filter admits, in the scope asked, oldest first (ADR 0080)."""

    def __init__(self, operations: FlowOperationsPort) -> None:
        self._operations = operations

    def execute(self, command: ExportAccountOperationsCommand) -> Iterator[Operation]:
        owner = AccountOperations(command.account_id, command.scope)
        return self._operations.export(owner, command.query)
