from datetime import timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.flows.errors import FlowAccountNotFoundError, FlowNotFoundError
from autotrading.application.flows.ports import ReconciliationAlarmPorts
from autotrading.application.flows.reconcile_account import ReconcileAccountCommand, ReconcileAccountUseCase
from autotrading.application.flows.record_account_executions import RecordAccountExecutionsUseCase
from autotrading.domain.flows.account_reconciliation import AccountReading, ProtectionClosing
from autotrading.domain.flows.balance_comparison import BalanceComparison
from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
from autotrading.domain.flows.unattributable import UnattributableKind
from autotrading.domain.notifications.alert import AlertCause, AlertState
from autotrading.domain.orders.client_order_id import ClientOrderId
from autotrading.domain.orders.placed_protection import PlacedProtection
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.fakes.account_thresholds import FakeAccountThresholdsAdapter
from tests.fakes.alert_repository import InMemoryAlertRepositoryAdapter
from tests.fakes.closed_positions import InMemoryClosedPositionsAdapter
from tests.fakes.flow_ledger import InMemoryFlowLedgerAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.platform_orders import InMemoryPlatformOrdersAdapter
from tests.fakes.protection_closings import InMemoryProtectionClosingsAdapter
from tests.fakes.protection_repository import InMemoryProtectionRepositoryAdapter, ProtectionStore
from tests.fakes.reconciliation_alarm_notices import FakeReconciliationAlarmNoticeAdapter
from tests.fakes.reconciliation_repository import InMemoryReconciliationRepositoryAdapter
from tests.support.activity import READ_AT, a_fill, a_movement, a_position, an_activity
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId(uuid4())
ACCOUNT = uuid4()
BEFORE = READ_AT - timedelta(minutes=5)
MINUTE = timedelta(minutes=1)


class Bench:
    def __init__(self) -> None:
        self.store = FlowStore()
        self.activity = FakeAccountActivityAdapter()
        self.protections = ProtectionStore()
        self.orders = InMemoryPlatformOrdersAdapter(self.protections)
        self.readings = InMemoryReconciliationRepositoryAdapter()
        self.closed = InMemoryClosedPositionsAdapter()
        self.closed_by_protection = InMemoryProtectionClosingsAdapter()
        self.ledger = InMemoryFlowLedgerAdapter()
        flows = InMemoryFlowRepositoryAdapter(self.store, TENANT)
        self.thresholds = FakeAccountThresholdsAdapter({ACCOUNT: "test-1"})
        self.notices = FakeReconciliationAlarmNoticeAdapter()
        record = RecordAccountExecutionsUseCase(flows, self.activity, self.orders, self.ledger)
        alarms = ReconciliationAlarmPorts(self.thresholds, self.thresholds, self.notices)
        self.alerts = InMemoryAlertRepositoryAdapter({}, TENANT)
        self.use_case = ReconcileAccountUseCase(
            flows,
            self.activity,
            self.readings,
            self.closed,
            record,
            self.ledger,
            self.closed_by_protection,
            alarms,
            self.alerts,
        )

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


def test_the_alert_of_a_position_no_longer_open_is_resolved_and_the_others_stay_open(bench: Bench) -> None:
    flow = bench.flow("BTC")
    gone = bench.alerts.open(AlertCause.unattributable_position(ACCOUNT, "test-1", "SOL"))
    held = bench.alerts.open(AlertCause.unattributable_position(ACCOUNT, "test-1", "ETH"))
    elsewhere = bench.alerts.open(AlertCause.unattributable_position(uuid4(), "test-2", "SOL"))
    bench.activity.activities[ACCOUNT] = an_activity(positions=(a_position("ETH"),))

    bench.use_case.execute(ReconcileAccountCommand(flow.id))

    assert [bench.alerts.get(alert_id).state for alert_id in (gone, held, elsewhere)] == [
        AlertState.RESOLVED,
        AlertState.OPEN,
        AlertState.OPEN,
    ]


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
    bench.activity.activities[ACCOUNT] = an_activity(balance=Decimal(1200))
    bench.activity.movements[ACCOUNT] = [a_movement(Decimal(200))]

    outcome = bench.use_case.execute(ReconcileAccountCommand(flow.id))

    assert outcome.new_items == ()
    assert bench.readings.alarms == []


def test_a_movement_recorded_by_an_earlier_reconciliation_after_the_last_reading_explains_the_balance(
    bench: Bench,
) -> None:
    # ADR movimenti-del-conto-nel-registro-con-cursore: the movements are rows of the ledger, read once.
    flow = bench.flow("BTC")
    bench.ledger.movements[ACCOUNT] = [a_movement(Decimal(200))]
    bench.ledger.cursors[ACCOUNT] = READ_AT
    bench.readings.save_reading(AccountReading(ACCOUNT, BEFORE, {}, Decimal(1000)))
    bench.activity.activities[ACCOUNT] = an_activity(balance=Decimal(1200))

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


# ADR saldo-atteso-dalle-righe-del-registro-dopo-la-lettura-precedente: a reversal or a cash out records its closing
# before the reconciliation, which reads it from the ledger for the expected balance (Bug 633).
def test_an_execution_recorded_before_the_reconciliation_explains_the_balance(bench: Bench) -> None:
    flow, order = bench.flow("BTC"), uuid4()
    bench.orders.add(order, ACCOUNT, flow.id)
    bench.readings.save_reading(AccountReading(ACCOUNT, BEFORE, {}, Decimal(1000)))
    closing = a_fill("BTC", order, realized_pnl=Decimal("4.6"), fee=Decimal("0.1"), executed_at=BEFORE + MINUTE)
    bench.ledger.add(ACCOUNT, flow.id, closing)
    bench.activity.executions[ACCOUNT] = [closing]
    bench.activity.activities[ACCOUNT] = an_activity(balance=Decimal("1004.5"))

    outcome = bench.use_case.execute(ReconcileAccountCommand(flow.id))

    assert outcome.new_items == ()
    assert bench.readings.alarms == []
    assert bench.readings.readings[ACCOUNT].comparison == BalanceComparison(
        Decimal("1004.5"), Decimal("1004.5"), READ_AT
    )
    assert bench.ledger.asked_after == [(ACCOUNT, BEFORE)]


def test_without_a_previous_reading_the_ledger_is_not_read_for_the_balance(bench: Bench) -> None:
    flow = bench.flow("BTC")
    bench.activity.activities[ACCOUNT] = an_activity()

    bench.use_case.execute(ReconcileAccountCommand(flow.id))

    assert bench.ledger.asked_after == []


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


def placed(bench: Bench, flow: Flow, kind: ProtectionKind) -> ClientOrderId:
    """A protection the flow placed on the asset, then removed: its execution still belongs to the flow."""
    client_order_id = ClientOrderId.new()
    protections = InMemoryProtectionRepositoryAdapter(bench.protections, TENANT)
    protections.add(PlacedProtection(ACCOUNT, flow.id.value, "BTC", kind, Decimal(57000), "41", client_order_id))
    protections.remove(ACCOUNT, "BTC")
    return client_order_id


@pytest.mark.parametrize(
    ("kind", "reason"),
    [(ProtectionKind.STOP_LOSS, CloseReason.STOP_LOSS), (ProtectionKind.TAKE_PROFIT, CloseReason.TAKE_PROFIT)],
)
def test_a_position_its_protection_closed_enters_the_history_by_its_protection(
    bench: Bench, kind: ProtectionKind, reason: CloseReason
) -> None:
    flow = bench.flow("BTC")
    order = placed(bench, flow, kind)
    bench.readings.save_reading(AccountReading(ACCOUNT, BEFORE, {flow.id: frozenset({"BTC"})}))
    bench.activity.activities[ACCOUNT] = an_activity()
    bench.activity.executions[ACCOUNT] = [
        a_fill("BTC", order.value, realized_pnl=Decimal("-3"), fee=Decimal("0.01"), fill_id="1"),
        a_fill("BTC", order.value, realized_pnl=Decimal("-2.1"), fee=Decimal("0.02"), fill_id="2"),
    ]

    outcome = bench.use_case.execute(ReconcileAccountCommand(flow.id))

    assert bench.closed_by_protection.closed == [
        ProtectionClosing(flow.id, "BTC", reason, Decimal("-5.1"), Decimal("0.03"), READ_AT)
    ]
    assert (bench.closed.closed, outcome.closed_outside, outcome.new_items) == ([], (), ())


def test_a_position_closed_by_an_order_of_the_flow_is_no_closing_by_protection(bench: Bench) -> None:
    flow, order = bench.flow("BTC"), uuid4()
    bench.orders.add(order, ACCOUNT, flow.id)
    bench.readings.save_reading(AccountReading(ACCOUNT, BEFORE, {flow.id: frozenset({"BTC"})}))
    bench.activity.activities[ACCOUNT] = an_activity()
    bench.activity.executions[ACCOUNT] = [a_fill("BTC", order)]

    bench.use_case.execute(ReconcileAccountCommand(flow.id))

    assert (bench.closed_by_protection.closed, bench.closed.closed) == ([], [])


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
