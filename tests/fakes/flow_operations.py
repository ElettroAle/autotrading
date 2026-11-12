"""In-memory reading of the ledger by its owner, newest first and a page at a time, as the SQL adapter reads it."""

from collections.abc import Callable, Iterable
from uuid import UUID

from autotrading.application.flows.errors import FlowAccountNotFoundError
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.ledger import ZERO, FundingEntry, LedgerEntry
from autotrading.domain.flows.operations import (
    FUNDING,
    Operation,
    OperationCursor,
    OperationSource,
    OperationsPage,
    OperationsQuery,
)
from tests.fakes.flow_ledger import InMemoryFlowLedgerAdapter

type Row = tuple[UUID, FlowId | None, Operation]


class InMemoryFlowOperationsAdapter:
    def __init__(self, ledger: InMemoryFlowLedgerAdapter, accounts: Callable[[], Iterable[UUID]]) -> None:
        self._ledger = ledger
        self._accounts = accounts

    def of_flow(self, flow_id: FlowId, query: OperationsQuery) -> OperationsPage:
        return self._page([operation for _, owner, operation in self._rows() if owner == flow_id], query)

    def unattributed_of_account(self, account_id: UUID, query: OperationsQuery) -> OperationsPage:
        if account_id not in set(self._accounts()):
            raise FlowAccountNotFoundError
        rows = self._rows()
        return self._page(
            [operation for account, owner, operation in rows if account == account_id and owner is None], query
        )

    @staticmethod
    def _page(operations: list[Operation], query: OperationsQuery) -> OperationsPage:
        admitted = sorted((operation for operation in operations if query.admits(operation)), key=lambda o: o.cursor)
        return OperationsPage.of(admitted[::-1][: query.limit + 1], query.limit)

    def _rows(self) -> list[Row]:
        executions = [(account, entry) for account, entries in self._ledger.entries.items() for entry in entries]
        payments = [(account, entry) for account, entries in self._ledger.funding.items() for entry in entries]
        rows = [_of_execution(account, entry, row_id) for row_id, (account, entry) in enumerate(executions, 1)]
        start = len(executions) + 1
        return rows + [_of_funding(account, entry, row_id) for row_id, (account, entry) in enumerate(payments, start)]


def _of_execution(account: UUID, entry: LedgerEntry, row_id: int) -> Row:
    execution = entry.execution
    cursor = OperationCursor(execution.executed_at, OperationSource.EXECUTION, row_id)
    operation = Operation(
        cursor,
        execution.asset,
        entry.kind.value,
        execution.size,
        execution.price,
        execution.fee,
        execution.realized_pnl,
        ZERO,
    )
    return account, entry.flow_id, operation


def _of_funding(account: UUID, entry: FundingEntry, row_id: int) -> Row:
    payment = entry.payment
    cursor = OperationCursor(payment.paid_at, OperationSource.FUNDING, row_id)
    return account, entry.flow_id, Operation(cursor, payment.asset, FUNDING, None, None, ZERO, ZERO, payment.amount)
