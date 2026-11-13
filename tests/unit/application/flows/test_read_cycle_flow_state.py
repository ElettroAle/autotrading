from collections.abc import Sequence
from datetime import datetime
from uuid import UUID, uuid4

import pytest

from autotrading.application.flows.errors import FlowExchangeUnavailableError, FlowPositionMismatchError
from autotrading.application.flows.read_cycle_flow_state import ReadCycleFlowStateCommand, ReadCycleFlowStateUseCase
from autotrading.application.flows.read_flow_state import ReadFlowStateUseCase
from autotrading.application.flows.reconcile_account import ReconcileAccountUseCase
from autotrading.application.flows.reconcile_account_for_cycle import (
    ReconcileAccountForCycleCommand,
    ReconcileAccountForCycleUseCase,
)
from autotrading.application.flows.record_account_executions import RecordAccountExecutionsUseCase
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.ledger import ExecutionsWindow
from autotrading.domain.flows.unattributable import UnattributableItem
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.fakes.closed_positions import InMemoryClosedPositionsAdapter
from tests.fakes.flow_ledger import InMemoryFlowLedgerAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.platform_orders import InMemoryPlatformOrdersAdapter
from tests.fakes.reconciliation_repository import InMemoryReconciliationRepositoryAdapter
from tests.support.activity import a_fill, a_position, an_activity
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId(uuid4())
ACCOUNT = uuid4()


class SilentExecutionsAdapter(FakeAccountActivityAdapter):
    """The positions of the account answer; its executions answer only while `executions_reachable`."""

    def __init__(self) -> None:
        super().__init__()
        self.executions_reachable = True

    def since(self, account_id: UUID, since: datetime | None) -> ExecutionsWindow:
        if not self.executions_reachable:
            raise FlowExchangeUnavailableError
        return super().since(account_id, since)


class RecordedNotices:
    def __init__(self) -> None:
        self.items: list[UnattributableItem] = []

    def execute(self, items: Sequence[UnattributableItem]) -> None:
        self.items.extend(items)


class Bench:
    def __init__(self) -> None:
        self.store = FlowStore()
        self.activity = SilentExecutionsAdapter()
        self.orders = InMemoryPlatformOrdersAdapter()
        self.ledger = InMemoryFlowLedgerAdapter()
        self.notices = RecordedNotices()
        flows = InMemoryFlowRepositoryAdapter(self.store, TENANT)
        record = RecordAccountExecutionsUseCase(flows, self.activity, self.orders, self.ledger)
        reconcile_account = ReconcileAccountUseCase(
            flows, self.activity, InMemoryReconciliationRepositoryAdapter(), InMemoryClosedPositionsAdapter(), record
        )
        self.reconcile = ReconcileAccountForCycleUseCase(reconcile_account, self.notices)
        self.read = ReadCycleFlowStateUseCase(ReadFlowStateUseCase(flows, self.activity, self.ledger), self.reconcile)
        self.flow = a_flow(
            TENANT, account_id=ACCOUNT, status=FlowStatus.ACTIVE, configuration=a_configuration(assets=("BTC",))
        )
        self.store.flows.append(self.flow)

    def hold_unexpected_position(self) -> None:
        self.activity.activities[ACCOUNT] = an_activity(positions=(a_position("BTC"),))

    def publish_execution_of_the_flow(self) -> None:
        order = uuid4()
        self.orders.add(order, ACCOUNT, self.flow.id)
        self.activity.executions[ACCOUNT] = [a_fill("BTC", order)]


@pytest.fixture
def bench() -> Bench:
    return Bench()


def started(bench: Bench, *, reconciled: bool = True) -> Flow:
    bench.read.execute(ReadCycleFlowStateCommand(bench.flow.id, reconciled))
    return bench.flow


def test_a_reconciliation_tells_the_new_cases_and_says_it_reconciled(bench: Bench) -> None:
    bench.activity.activities[ACCOUNT] = an_activity(positions=(a_position("SOL"),))

    assert bench.reconcile.execute(ReconcileAccountForCycleCommand(bench.flow.id)) is True
    assert [item.asset for item in bench.notices.items] == ["SOL"]


def test_an_account_out_of_reach_is_not_reconciled_and_the_flows_keep_operating(bench: Bench) -> None:
    bench.activity.executions_reachable = False

    assert bench.reconcile.execute(ReconcileAccountForCycleCommand(bench.flow.id)) is False
    assert bench.notices.items == []


def test_a_flow_whose_positions_match_its_ledger_starts_from_its_state(bench: Bench) -> None:
    state = bench.read.execute(ReadCycleFlowStateCommand(bench.flow.id, reconciled=True))

    assert state.flow_id == bench.flow.id
    assert state.position_mismatch() is None


def test_without_a_reconciliation_the_comparison_waits_for_the_next_cycle(bench: Bench) -> None:
    bench.hold_unexpected_position()

    state = bench.read.execute(ReadCycleFlowStateCommand(bench.flow.id, reconciled=False))

    assert state.position_mismatch() is not None


def test_a_difference_the_executions_do_not_explain_stops_the_flow(bench: Bench) -> None:
    bench.hold_unexpected_position()

    with pytest.raises(FlowPositionMismatchError, match=r"^posizione BTC diversa da quella del flusso"):
        started(bench)


def test_an_execution_published_meanwhile_explains_the_difference(bench: Bench) -> None:
    bench.hold_unexpected_position()
    bench.publish_execution_of_the_flow()

    state = bench.read.execute(ReadCycleFlowStateCommand(bench.flow.id, reconciled=True))

    assert state.position_mismatch() is None


def test_executions_out_of_reach_fail_the_cycle_without_pausing_the_flow(bench: Bench) -> None:
    bench.hold_unexpected_position()
    bench.activity.executions_reachable = False

    with pytest.raises(FlowExchangeUnavailableError):
        started(bench)
