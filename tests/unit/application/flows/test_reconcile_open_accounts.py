"""The periodic check of the accounts whose flows hold open positions (Bug 778, ADR
riconciliazione-periodica-dei-conti-con-posizioni-aperte)."""

import logging
from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from autotrading.application.flows.ports import ReconciliationAlarmPorts
from autotrading.application.flows.reconcile_account import ReconcileAccountUseCase
from autotrading.application.flows.reconcile_account_for_cycle import ReconcileAccountForCycleUseCase
from autotrading.application.flows.reconcile_open_accounts import (
    OpenAccountReadings,
    ReconcileOpenAccountsCommand,
    ReconcileOpenAccountsUseCase,
)
from autotrading.application.flows.record_account_executions import RecordAccountExecutionsUseCase
from autotrading.domain.flows.account_activity import AccountActivity
from autotrading.domain.flows.account_reconciliation import AccountReading
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.fakes.account_reconciliation_intervals import FakeAccountReconciliationIntervalsAdapter
from tests.fakes.account_thresholds import FakeAccountThresholdsAdapter
from tests.fakes.alert_repository import InMemoryAlertRepositoryAdapter
from tests.fakes.closed_positions import InMemoryClosedPositionsAdapter
from tests.fakes.cycles import FakeClockAdapter, InMemoryFlowLockAdapter
from tests.fakes.flow_ledger import InMemoryFlowLedgerAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.platform_orders import InMemoryPlatformOrdersAdapter
from tests.fakes.protection_closings import InMemoryProtectionClosingsAdapter
from tests.fakes.protection_repository import ProtectionStore
from tests.fakes.reconciliation_alarm_notices import FakeReconciliationAlarmNoticeAdapter
from tests.fakes.reconciliation_repository import InMemoryReconciliationRepositoryAdapter
from tests.support.activity import READ_AT, an_activity
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId(uuid4())
ACCOUNT, OTHER_ACCOUNT = uuid4(), uuid4()
INTERVAL = timedelta(minutes=5)
WARNING = "riconciliazione periodica del conto interrotta"


class Notices:
    """The new cases the check tells the user, as the cycle tells them (R1.8.2)."""

    def __init__(self) -> None:
        self.told: list[object] = []

    def execute(self, items: object) -> None:
        self.told.append(items)


class Bench:
    def __init__(self) -> None:
        self.store = FlowStore()
        self.activity = FakeAccountActivityAdapter()
        self.readings = InMemoryReconciliationRepositoryAdapter()
        self.intervals = FakeAccountReconciliationIntervalsAdapter({ACCOUNT, OTHER_ACCOUNT})
        self.lock = InMemoryFlowLockAdapter()
        self.clock = FakeClockAdapter(READ_AT)
        self.notices = Notices()
        flows = InMemoryFlowRepositoryAdapter(self.store, TENANT)
        thresholds = FakeAccountThresholdsAdapter({ACCOUNT: "principale", OTHER_ACCOUNT: "secondario"})
        ledger = InMemoryFlowLedgerAdapter()
        reconcile_account = ReconcileAccountUseCase(
            flows,
            self.activity,
            self.readings,
            InMemoryClosedPositionsAdapter(),
            RecordAccountExecutionsUseCase(
                flows, self.activity, InMemoryPlatformOrdersAdapter(ProtectionStore()), ledger
            ),
            ledger,
            InMemoryProtectionClosingsAdapter(),
            ReconciliationAlarmPorts(thresholds, thresholds, FakeReconciliationAlarmNoticeAdapter()),
            InMemoryAlertRepositoryAdapter({}, TENANT),
        )
        self.use_case = ReconcileOpenAccountsUseCase(
            flows,
            OpenAccountReadings(self.readings, self.intervals, self.clock),
            self.lock,
            ReconcileAccountForCycleUseCase(reconcile_account, self.notices),
        )

    def flow(self, *assets: str, account_id: UUID = ACCOUNT, status: FlowStatus = FlowStatus.ACTIVE) -> Flow:
        flow = a_flow(TENANT, account_id=account_id, status=status, configuration=a_configuration(assets=assets))
        self.store.flows.append(flow)
        return flow

    def read_with(self, flow: Flow, *assets: str, ago: timedelta = INTERVAL) -> AccountReading:
        """The last reading of the account of the flow, that long ago, with those assets open."""
        reading = AccountReading(flow.assigned_account_id, READ_AT - ago, {flow.id: frozenset(assets)})
        self.readings.save_reading(reading)
        return reading

    def check(self) -> None:
        self.use_case.execute(ReconcileOpenAccountsCommand())


@pytest.fixture
def bench() -> Bench:
    return Bench()


def test_an_account_with_open_positions_is_reconciled_once_its_interval_has_passed(bench: Bench) -> None:
    account_id = bench.read_with(bench.flow("BTC"), "BTC").account_id

    bench.check()

    assert bench.activity.read == [account_id]
    reading = bench.readings.last_reading(ACCOUNT)
    assert reading is not None
    assert reading.read_at == READ_AT


def test_the_new_cases_are_told_as_in_the_cycle(bench: Bench) -> None:
    bench.read_with(bench.flow("BTC"), "BTC")

    bench.check()

    assert bench.notices.told == [()]


def test_an_account_whose_interval_has_not_passed_is_not_read(bench: Bench) -> None:
    flow = bench.flow("BTC")
    bench.read_with(flow, "BTC")
    bench.intervals.intervals[ACCOUNT] = timedelta(minutes=15)

    bench.check()

    assert bench.activity.read == []


def test_an_account_without_open_positions_is_not_read(bench: Bench) -> None:
    bench.read_with(bench.flow("BTC"))

    bench.check()

    assert bench.activity.read == []


def test_an_account_never_read_is_left_to_the_cycle(bench: Bench) -> None:
    bench.flow("BTC")

    bench.check()

    assert bench.activity.read == []


def test_drafts_and_archived_flows_take_no_account(bench: Bench) -> None:
    for status in (FlowStatus.DRAFT, FlowStatus.ARCHIVED):
        bench.read_with(bench.flow("BTC", account_id=OTHER_ACCOUNT, status=status), "BTC")

    bench.check()

    assert bench.activity.read == []


def test_an_account_whose_cycle_is_running_is_left_to_the_cycle(bench: Bench) -> None:
    alfa = bench.flow("BTC")
    beta = bench.flow("ETH")
    before = bench.read_with(alfa, "BTC")

    with bench.lock.hold(beta.id.value) as running:
        assert running
        bench.check()

    assert bench.activity.read == []
    assert bench.readings.last_reading(ACCOUNT) == before
    with bench.lock.hold(alfa.id.value) as free:
        assert free


def test_every_flow_of_the_account_is_held_while_it_is_reconciled(bench: Bench) -> None:
    alfa, beta = bench.flow("BTC"), bench.flow("ETH")
    bench.read_with(alfa, "BTC")
    held: list[bool] = []

    def reading_under_the_lock(_: UUID) -> AccountActivity:
        for flow in (alfa, beta):
            with bench.lock.hold(flow.id.value) as free:
                held.append(not free)
        return an_activity()

    bench.activity.unread = reading_under_the_lock

    bench.check()

    assert held == [True, True]
    with bench.lock.hold(alfa.id.value) as free:
        assert free


def test_an_exchange_that_does_not_answer_leaves_the_account_for_the_next_check(
    bench: Bench, caplog: pytest.LogCaptureFixture
) -> None:
    flow = bench.flow("BTC")
    before = bench.read_with(flow, "BTC")
    bench.activity.reachable = False

    with caplog.at_level(logging.WARNING, logger="autotrading.flows"):
        bench.check()

    assert bench.readings.last_reading(ACCOUNT) == before
    assert bench.store.flows == [flow]
    assert "riconciliazione del conto non riuscita" in caplog.messages


def test_an_error_on_one_account_leaves_the_others_going(bench: Bench, caplog: pytest.LogCaptureFixture) -> None:
    unknown = bench.flow("BTC", account_id=uuid4())
    bench.read_with(unknown, "BTC")
    bench.read_with(bench.flow("ETH", account_id=OTHER_ACCOUNT), "ETH")

    with caplog.at_level(logging.WARNING, logger="autotrading.flows"):
        bench.check()

    assert bench.activity.read == [OTHER_ACCOUNT]
    [record] = [record for record in caplog.records if record.message == WARNING]
    assert record.__dict__["account_id"] == str(unknown.assigned_account_id)
