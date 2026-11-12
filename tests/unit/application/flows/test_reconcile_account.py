from datetime import timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.flows.errors import FlowNotFoundError
from autotrading.application.flows.reconcile_account import ReconcileAccountCommand, ReconcileAccountUseCase
from autotrading.application.flows.record_account_executions import RecordAccountExecutionsUseCase
from autotrading.domain.flows.account_reconciliation import OUTSIDE_PLATFORM, AccountReading
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.unattributable import UnattributableKind
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.fakes.closed_positions import InMemoryClosedPositionsAdapter
from tests.fakes.flow_ledger import InMemoryFlowLedgerAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.platform_orders import InMemoryPlatformOrdersAdapter
from tests.fakes.reconciliation_repository import InMemoryReconciliationRepositoryAdapter
from tests.support.activity import READ_AT, a_fill, a_movement, a_position, an_activity
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId(uuid4())
ACCOUNT = uuid4()
BEFORE = READ_AT - timedelta(minutes=5)


class Bench:
    def __init__(self) -> None:
        self.store = FlowStore()
        self.activity = FakeAccountActivityAdapter()
        self.orders = InMemoryPlatformOrdersAdapter()
        self.readings = InMemoryReconciliationRepositoryAdapter()
        self.closed = InMemoryClosedPositionsAdapter()
        self.ledger = InMemoryFlowLedgerAdapter()
        flows = InMemoryFlowRepositoryAdapter(self.store, TENANT)
        record = RecordAccountExecutionsUseCase(flows, self.activity, self.orders, self.ledger)
        self.use_case = ReconcileAccountUseCase(flows, self.activity, self.readings, self.closed, record)

    def flow(self, *assets: str, account_id: UUID = ACCOUNT) -> Flow:
        flow = a_flow(
            TENANT,
            account_id=account_id,
            status=FlowStatus.ACTIVE,
            configuration=a_configuration(assets=assets),
        )
        self.store.flows.append(flow)
        return flow


@pytest.fixture
def bench() -> Bench:
    return Bench()


def test_a_new_case_is_recorded_and_reported(bench: Bench) -> None:
    flow = bench.flow("BTC")
    bench.activity.activities[ACCOUNT] = an_activity(positions=(a_position("SOL"),))

    outcome = bench.use_case.execute(ReconcileAccountCommand(flow.id))

    assert [item.reference for item in outcome.new_items] == ["SOL"]
    assert [item.kind for item in bench.readings.items] == [UnattributableKind.POSITION]


def test_a_case_already_recorded_is_not_reported_again(bench: Bench) -> None:
    flow = bench.flow("BTC")
    bench.activity.activities[ACCOUNT] = an_activity(positions=(a_position("SOL"),))
    bench.use_case.execute(ReconcileAccountCommand(flow.id))

    outcome = bench.use_case.execute(ReconcileAccountCommand(flow.id))

    assert outcome.new_items == ()
    assert len(bench.readings.items) == 1


def test_a_recorded_position_no_longer_open_is_resolved(bench: Bench) -> None:
    flow = bench.flow("BTC")
    bench.activity.activities[ACCOUNT] = an_activity(positions=(a_position("SOL"),))
    bench.use_case.execute(ReconcileAccountCommand(flow.id))
    bench.activity.activities[ACCOUNT] = an_activity()

    bench.use_case.execute(ReconcileAccountCommand(flow.id))

    assert [item.reference for item in bench.readings.resolved] == ["SOL"]


def test_the_flows_of_the_same_account_own_their_assets(bench: Bench) -> None:
    alfa = bench.flow("BTC")
    bench.flow("ETH")
    bench.flow("SOL", account_id=uuid4())
    bench.activity.activities[ACCOUNT] = an_activity(positions=(a_position("ETH"), a_position("SOL")))

    outcome = bench.use_case.execute(ReconcileAccountCommand(alfa.id))

    assert [item.reference for item in outcome.new_items] == ["SOL"]


def test_the_reading_is_saved_for_the_next_reconciliation(bench: Bench) -> None:
    flow = bench.flow("BTC")
    bench.activity.activities[ACCOUNT] = an_activity(positions=(a_position("BTC"),))

    bench.use_case.execute(ReconcileAccountCommand(flow.id))

    assert bench.readings.readings[ACCOUNT] == AccountReading(ACCOUNT, READ_AT, {flow.id: frozenset({"BTC"})})


def test_a_movement_after_the_saved_reading_is_recorded(bench: Bench) -> None:
    flow = bench.flow("BTC")
    bench.readings.save_reading(AccountReading(ACCOUNT, BEFORE, {}))
    bench.activity.activities[ACCOUNT] = an_activity(movements=(a_movement(Decimal(200)),))

    outcome = bench.use_case.execute(ReconcileAccountCommand(flow.id))

    assert [(item.kind, item.amount) for item in outcome.new_items] == [
        (UnattributableKind.BALANCE_CHANGE, Decimal(200))
    ]


def test_the_fills_of_the_orders_of_the_platform_are_explained(bench: Bench) -> None:
    flow, order = bench.flow("BTC"), uuid4()
    bench.orders.add(order, ACCOUNT, flow.id)
    bench.readings.save_reading(AccountReading(ACCOUNT, BEFORE, {}))
    bench.activity.activities[ACCOUNT] = an_activity()
    bench.activity.executions[ACCOUNT] = [a_fill("BTC", order), a_fill("BTC", None, fill_id="9")]

    outcome = bench.use_case.execute(ReconcileAccountCommand(flow.id))

    assert [item.reference for item in outcome.new_items] == ["9"]


def test_the_executions_are_recorded_in_the_ledger_before_the_reconciliation(bench: Bench) -> None:
    flow, order = bench.flow("BTC"), uuid4()
    bench.orders.add(order, ACCOUNT, flow.id)
    bench.activity.activities[ACCOUNT] = an_activity()
    bench.activity.executions[ACCOUNT] = [a_fill("BTC", order, realized_pnl=Decimal(4))]

    bench.use_case.execute(ReconcileAccountCommand(flow.id))

    assert bench.ledger.realized(flow.id) == Decimal(4)


def test_executions_already_recorded_are_not_reported_again(bench: Bench) -> None:
    flow = bench.flow("BTC")
    bench.readings.save_reading(AccountReading(ACCOUNT, BEFORE, {}))
    bench.activity.activities[ACCOUNT] = an_activity()
    bench.activity.executions[ACCOUNT] = [a_fill("BTC", None, fill_id="9")]
    bench.use_case.execute(ReconcileAccountCommand(flow.id))

    outcome = bench.use_case.execute(ReconcileAccountCommand(flow.id))

    assert outcome.new_items == ()


def test_a_position_closed_outside_enters_the_history_of_the_flow(bench: Bench) -> None:
    flow = bench.flow("BTC")
    bench.readings.save_reading(AccountReading(ACCOUNT, BEFORE, {flow.id: frozenset({"BTC"})}))
    bench.activity.activities[ACCOUNT] = an_activity()

    outcome = bench.use_case.execute(ReconcileAccountCommand(flow.id))

    assert [(closing.asset, closing.reason) for closing in bench.closed.closed] == [("BTC", OUTSIDE_PLATFORM)]
    assert outcome.closed_outside == tuple(bench.closed.closed)


def test_an_unknown_flow_is_not_found(bench: Bench) -> None:
    with pytest.raises(FlowNotFoundError):
        bench.use_case.execute(ReconcileAccountCommand(FlowId.new()))
