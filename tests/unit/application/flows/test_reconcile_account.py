from datetime import timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.flows.errors import FlowAccountNotFoundError, FlowNotFoundError
from autotrading.application.flows.ports import ReconciliationAlarmPorts
from autotrading.application.flows.reconcile_account import ReconcileAccountCommand, ReconcileAccountUseCase
from autotrading.application.flows.record_account_executions import RecordAccountExecutionsUseCase
from autotrading.domain.flows.account_reconciliation import AccountReading
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
from autotrading.domain.flows.unattributable import UnattributableKind
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.fakes.account_thresholds import FakeAccountThresholdsAdapter
from tests.fakes.closed_positions import InMemoryClosedPositionsAdapter
from tests.fakes.flow_ledger import InMemoryFlowLedgerAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.platform_orders import InMemoryPlatformOrdersAdapter
from tests.fakes.reconciliation_alarm_notices import FakeReconciliationAlarmNoticeAdapter
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
        self.thresholds = FakeAccountThresholdsAdapter({ACCOUNT: "test-1"})
        self.notices = FakeReconciliationAlarmNoticeAdapter()
        record = RecordAccountExecutionsUseCase(flows, self.activity, self.orders, self.ledger)
        alarms = ReconciliationAlarmPorts(self.thresholds, self.thresholds, self.notices)
        self.use_case = ReconcileAccountUseCase(flows, self.activity, self.readings, self.closed, record, alarms)

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

    assert bench.readings.readings[ACCOUNT] == AccountReading(
        ACCOUNT, READ_AT, {flow.id: frozenset({"BTC"})}, Decimal(1000)
    )


def test_a_movement_the_exchange_declares_explains_the_balance(bench: Bench) -> None:
    flow = bench.flow("BTC")
    bench.readings.save_reading(AccountReading(ACCOUNT, BEFORE, {}, Decimal(1000)))
    bench.activity.activities[ACCOUNT] = an_activity(balance=Decimal(1200), movements=(a_movement(Decimal(200)),))

    outcome = bench.use_case.execute(ReconcileAccountCommand(flow.id))

    assert outcome.new_items == ()
    assert bench.readings.alarms == []


def test_an_unexplained_change_within_the_threshold_is_recorded_and_reported(bench: Bench) -> None:
    flow = bench.flow("BTC")
    bench.readings.save_reading(AccountReading(ACCOUNT, BEFORE, {}, Decimal(1000)))
    bench.activity.activities[ACCOUNT] = an_activity(balance=Decimal(995))

    outcome = bench.use_case.execute(ReconcileAccountCommand(flow.id))

    assert [(item.kind, item.amount) for item in outcome.new_items] == [
        (UnattributableKind.BALANCE_CHANGE, Decimal(-5))
    ]
    assert bench.readings.readings[ACCOUNT].reference_balance == Decimal(995)


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

    assert [closing.asset for closing in bench.closed.closed] == ["BTC"]
    assert outcome.closed_outside == tuple(bench.closed.closed)


def test_an_unknown_flow_is_not_found(bench: Bench) -> None:
    with pytest.raises(FlowNotFoundError):
        bench.use_case.execute(ReconcileAccountCommand(FlowId.new()))


def test_a_balance_beyond_the_threshold_opens_an_alarm_and_tells_the_user(bench: Bench) -> None:
    flow = bench.flow("BTC")
    bench.readings.save_reading(AccountReading(ACCOUNT, BEFORE, {}, Decimal(1000)))
    bench.activity.activities[ACCOUNT] = an_activity(balance=Decimal(980))

    bench.use_case.execute(ReconcileAccountCommand(flow.id))

    assert bench.readings.alarms == [ReconciliationAlarm(ACCOUNT, Decimal(1000), Decimal(980), Decimal(2), READ_AT)]
    assert bench.notices.told == [("test-1", Decimal(980), Decimal(1000))]
    assert bench.readings.readings[ACCOUNT].reference_balance == Decimal(1000)


def test_an_alarm_already_open_is_neither_opened_nor_told_again(bench: Bench) -> None:
    flow = bench.flow("BTC")
    bench.readings.save_reading(AccountReading(ACCOUNT, BEFORE, {}, Decimal(1000)))
    bench.activity.activities[ACCOUNT] = an_activity(balance=Decimal(980))
    bench.use_case.execute(ReconcileAccountCommand(flow.id))

    bench.use_case.execute(ReconcileAccountCommand(flow.id))

    assert len(bench.readings.alarms) == 1
    assert len(bench.notices.told) == 1


def test_the_threshold_of_the_account_decides_the_alarm(bench: Bench) -> None:
    flow = bench.flow("BTC")
    bench.thresholds.thresholds[ACCOUNT] = Decimal(3)
    bench.readings.save_reading(AccountReading(ACCOUNT, BEFORE, {}, Decimal(1000)))
    bench.activity.activities[ACCOUNT] = an_activity(balance=Decimal(980))

    bench.use_case.execute(ReconcileAccountCommand(flow.id))

    assert bench.readings.alarms == []
    assert bench.notices.told == []


def test_an_account_the_tenant_does_not_have_is_not_reconciled(bench: Bench) -> None:
    flow = bench.flow("BTC", account_id=uuid4())

    with pytest.raises(FlowAccountNotFoundError):
        bench.use_case.execute(ReconcileAccountCommand(flow.id))

    assert bench.readings.readings == {}
