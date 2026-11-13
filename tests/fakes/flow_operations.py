"""In-memory reading of the ledger by its owner, as the SQL adapter reads it: pages newest first with the totals of the
whole filter, and the export oldest first.
"""

from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import replace
from uuid import UUID

from autotrading.application.flows.errors import FlowAccountNotFoundError
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.ledger import ZERO, FundingEntry, LedgerEntry
from autotrading.domain.flows.operations import (
    FUNDING,
    AccountOperations,
    AccountScope,
    FlowOperations,
    Operation,
    OperationCursor,
    OperationSource,
    OperationsOwner,
    OperationsPage,
    OperationsQuery,
    OperationsReport,
    OperationsTotals,
)
from tests.fakes.flow_ledger import InMemoryFlowLedgerAdapter

type Row = tuple[UUID, FlowId | None, Operation]


def no_flow_names() -> Mapping[FlowId, str]:
    return {}


class InMemoryFlowOperationsAdapter:
    def __init__(
        self,
        ledger: InMemoryFlowLedgerAdapter,
        accounts: Callable[[], Iterable[UUID]],
        flow_names: Callable[[], Mapping[FlowId, str]] = no_flow_names,
    ) -> None:
        self._ledger = ledger
        self._accounts = accounts
        self._flow_names = flow_names

    def report(self, owner: OperationsOwner, query: OperationsQuery) -> OperationsReport:
        rows = self._owned(owner)
        admitted = sorted((row for row in rows if query.admits(row)), key=lambda row: row.cursor, reverse=True)
        whole = [row for row in rows if query.unpaged().admits(row)]
        totals = OperationsTotals(
            len(whole),
            sum((row.realized_pnl for row in whole), ZERO),
            sum((row.fee for row in whole), ZERO),
            sum((row.funding for row in whole), ZERO),
        )
        return OperationsReport(OperationsPage.of(admitted[: query.limit + 1], query.limit), totals)

    def export(self, owner: OperationsOwner, query: OperationsQuery) -> Iterator[Operation]:
        rows = self._owned(owner)
        return iter(sorted((row for row in rows if query.unpaged().admits(row)), key=lambda row: row.cursor))

    def _owned(self, owner: OperationsOwner) -> list[Operation]:
        match owner:
            case FlowOperations(flow_id):
                return [operation for _, flow, operation in self._rows() if flow == flow_id]
            case AccountOperations(account_id, scope):
                if account_id not in set(self._accounts()):
                    raise FlowAccountNotFoundError
                return [
                    operation
                    for account, flow, operation in self._rows()
                    if account == account_id and (scope is AccountScope.ALL or flow is None)
                ]

    def _rows(self) -> list[Row]:
        names = self._flow_names()
        executions = [(account, entry) for account, entries in self._ledger.entries.items() for entry in entries]
        payments = [(account, entry) for account, entries in self._ledger.funding.items() for entry in entries]
        rows = [_of_execution(account, entry, row_id) for row_id, (account, entry) in enumerate(executions, 1)]
        start = len(executions) + 1
        rows += [_of_funding(account, entry, row_id) for row_id, (account, entry) in enumerate(payments, start)]
        return [
            (account, flow, operation if flow is None else replace(operation, flow=names.get(flow)))
            for account, flow, operation in rows
        ]


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
