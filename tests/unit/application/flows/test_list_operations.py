from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.flows.errors import FlowAccountNotFoundError, FlowNotFoundError
from autotrading.application.flows.export_account_operations import (
    ExportAccountOperationsCommand,
    ExportAccountOperationsUseCase,
)
from autotrading.application.flows.export_flow_operations import (
    ExportFlowOperationsCommand,
    ExportFlowOperationsUseCase,
)
from autotrading.application.flows.list_account_operations import (
    ListAccountOperationsCommand,
    ListAccountOperationsUseCase,
)
from autotrading.application.flows.list_flow_operations import ListFlowOperationsCommand, ListFlowOperationsUseCase
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.ledger import (
    AccountLedger,
    Execution,
    ExecutionKind,
    FundingEntry,
    FundingPayment,
    LedgerEntry,
)
from autotrading.domain.flows.operations import FUNDING, AccountScope, OperationsQuery, OperationsTotals
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.flow_ledger import InMemoryFlowLedgerAdapter
from tests.fakes.flow_operations import InMemoryFlowOperationsAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.support.flows import a_flow

TENANT = TenantId(uuid4())
AT = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)


def an_execution(fill_id: str, asset: str = "BTC") -> Execution:
    return Execution(
        fill_id, f"o-{fill_id}", None, asset, Decimal(1), Decimal(100), Decimal(0), Decimal(0), Decimal(0), False, AT
    )


def ledger_with(account_id: UUID, flow_id: FlowId) -> InMemoryFlowLedgerAdapter:
    ledger = InMemoryFlowLedgerAdapter()
    entries = (
        LedgerEntry(an_execution("del-flusso"), flow_id, ExecutionKind.FLOW_ORDER, platform_order=True),
        LedgerEntry(an_execution("di-nessuno", "SOL"), None, ExecutionKind.UNATTRIBUTED, platform_order=False),
    )
    funding = (FundingEntry(FundingPayment("BTC", Decimal(2), AT), flow_id),)
    ledger.record(account_id, AccountLedger(entries, funding), AT)
    return ledger


def test_the_operations_of_a_flow_are_its_executions_and_funding() -> None:
    account_id = uuid4()
    flow = a_flow(TENANT, account_id=account_id)
    store = FlowStore()
    store.flows.append(flow)
    operations = InMemoryFlowOperationsAdapter(ledger_with(account_id, flow.id), lambda: [account_id])
    use_case = ListFlowOperationsUseCase(InMemoryFlowRepositoryAdapter(store, TENANT), operations)

    report = use_case.execute(ListFlowOperationsCommand(flow.id.value, OperationsQuery()))

    assert [(operation.kind, operation.asset) for operation in report.page.operations] == [
        (FUNDING, "BTC"),
        (ExecutionKind.FLOW_ORDER.value, "BTC"),
    ]
    assert report.totals == OperationsTotals(2, Decimal(0), Decimal(0), Decimal(2))


def test_the_operations_of_a_flow_the_tenant_does_not_have_are_refused() -> None:
    operations = InMemoryFlowOperationsAdapter(InMemoryFlowLedgerAdapter(), list)
    use_case = ListFlowOperationsUseCase(InMemoryFlowRepositoryAdapter(FlowStore(), TENANT), operations)

    with pytest.raises(FlowNotFoundError):
        use_case.execute(ListFlowOperationsCommand(uuid4(), OperationsQuery()))


def test_the_operations_of_an_account_are_those_of_no_flow() -> None:
    account_id = uuid4()
    operations = InMemoryFlowOperationsAdapter(ledger_with(account_id, FlowId.new()), lambda: [account_id])

    command = ListAccountOperationsCommand(account_id, OperationsQuery(), AccountScope.UNATTRIBUTED)

    report = ListAccountOperationsUseCase(operations).execute(command)

    assert [(operation.kind, operation.asset) for operation in report.page.operations] == [
        (ExecutionKind.UNATTRIBUTED.value, "SOL")
    ]


def test_the_operations_of_an_account_the_tenant_does_not_have_are_refused() -> None:
    operations = InMemoryFlowOperationsAdapter(InMemoryFlowLedgerAdapter(), list)

    with pytest.raises(FlowAccountNotFoundError):
        ListAccountOperationsUseCase(operations).execute(
            ListAccountOperationsCommand(uuid4(), OperationsQuery(), AccountScope.ALL)
        )


def test_all_the_operations_of_an_account_name_their_flow() -> None:
    account_id = uuid4()
    flow_id = FlowId.new()
    operations = InMemoryFlowOperationsAdapter(
        ledger_with(account_id, flow_id), lambda: [account_id], lambda: {flow_id: "alfa"}
    )
    command = ListAccountOperationsCommand(account_id, OperationsQuery(), AccountScope.ALL)

    report = ListAccountOperationsUseCase(operations).execute(command)

    assert sorted((operation.asset, operation.kind, operation.flow or "") for operation in report.page.operations) == [
        ("BTC", FUNDING, "alfa"),
        ("BTC", ExecutionKind.FLOW_ORDER.value, "alfa"),
        ("SOL", ExecutionKind.UNATTRIBUTED.value, ""),
    ]


def test_the_export_of_a_flow_reads_every_row_oldest_first_whatever_the_page() -> None:
    account_id = uuid4()
    flow = a_flow(TENANT, account_id=account_id)
    store = FlowStore()
    store.flows.append(flow)
    operations = InMemoryFlowOperationsAdapter(ledger_with(account_id, flow.id), lambda: [account_id])
    use_case = ExportFlowOperationsUseCase(InMemoryFlowRepositoryAdapter(store, TENANT), operations)
    first = ListFlowOperationsUseCase(InMemoryFlowRepositoryAdapter(store, TENANT), operations).execute(
        ListFlowOperationsCommand(flow.id.value, OperationsQuery(limit=1))
    )

    exported = list(
        use_case.execute(ExportFlowOperationsCommand(flow.id.value, OperationsQuery(after=first.page.next)))
    )

    assert [operation.kind for operation in exported] == [ExecutionKind.FLOW_ORDER.value, FUNDING]


def test_the_export_of_a_flow_the_tenant_does_not_have_is_refused_before_any_row() -> None:
    operations = InMemoryFlowOperationsAdapter(InMemoryFlowLedgerAdapter(), list)
    use_case = ExportFlowOperationsUseCase(InMemoryFlowRepositoryAdapter(FlowStore(), TENANT), operations)

    with pytest.raises(FlowNotFoundError):
        use_case.execute(ExportFlowOperationsCommand(uuid4(), OperationsQuery()))


def test_the_export_of_an_account_reads_the_rows_of_its_scope() -> None:
    account_id = uuid4()
    operations = InMemoryFlowOperationsAdapter(ledger_with(account_id, FlowId.new()), lambda: [account_id])
    command = ExportAccountOperationsCommand(account_id, OperationsQuery(), AccountScope.UNATTRIBUTED)

    exported = list(ExportAccountOperationsUseCase(operations).execute(command))

    assert [operation.asset for operation in exported] == ["SOL"]


def test_the_export_of_an_account_the_tenant_does_not_have_is_refused() -> None:
    operations = InMemoryFlowOperationsAdapter(InMemoryFlowLedgerAdapter(), list)
    command = ExportAccountOperationsCommand(uuid4(), OperationsQuery(), AccountScope.ALL)

    with pytest.raises(FlowAccountNotFoundError):
        ExportAccountOperationsUseCase(operations).execute(command)
