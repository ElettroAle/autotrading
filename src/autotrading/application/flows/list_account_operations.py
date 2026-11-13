from dataclasses import dataclass
from uuid import UUID

from autotrading.application.flows.ports import FlowOperationsPort
from autotrading.domain.flows.operations import AccountOperations, AccountScope, OperationsQuery, OperationsReport


@dataclass(frozen=True, slots=True)
class ListAccountOperationsCommand:
    account_id: UUID
    query: OperationsQuery
    scope: AccountScope


class ListAccountOperationsUseCase:
    """The executions and funding payments of an account of the tenant, of no flow or of all of them, with the totals
    of the whole filter (ADR 0074, ADR 0080).
    """

    def __init__(self, operations: FlowOperationsPort) -> None:
        self._operations = operations

    def execute(self, command: ListAccountOperationsCommand) -> OperationsReport:
        return self._operations.report(AccountOperations(command.account_id, command.scope), command.query)
