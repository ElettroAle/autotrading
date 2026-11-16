"""The flow as a cycle reads it at its start, with the alarm of reconciliation of its account (R3.3.1)."""

from collections.abc import Sequence
from datetime import timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.flows.ports import ReconciliationAlarmPorts
from autotrading.application.flows.read_cycle_account import ReadCycleAccountUseCase
from autotrading.application.flows.read_cycle_flow import ReadCycleFlowCommand, ReadCycleFlowUseCase
from autotrading.application.flows.read_cycle_flow_state import ReadCycleFlowStateUseCase
from autotrading.application.flows.read_flow_state import ReadFlowStateUseCase
from autotrading.application.flows.reconcile_account import ReconcileAccountUseCase
from autotrading.application.flows.reconcile_account_for_cycle import ReconcileAccountForCycleUseCase
from autotrading.application.flows.record_account_executions import RecordAccountExecutionsUseCase
from autotrading.domain.flows.balance_comparison import BalanceComparison
from autotrading.domain.flows.cycle_access import CycleAccess
from autotrading.domain.flows.cycle_account import CycleAccount
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
from autotrading.domain.flows.sealed_address import SealedAddress
from autotrading.domain.flows.unattributable import UnattributableItem
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.fakes.account_thresholds import FakeAccountThresholdsAdapter
from tests.fakes.closed_positions import InMemoryClosedPositionsAdapter
from tests.fakes.exit_plan_repository import ExitPlanStore, InMemoryExitPlanRepositoryAdapter
from tests.fakes.flow_ledger import InMemoryFlowLedgerAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter, InMemoryFlowTimingAdapter
from tests.fakes.platform_orders import InMemoryPlatformOrdersAdapter
from tests.fakes.protection_closings import InMemoryProtectionClosingsAdapter
from tests.fakes.reconciliation_alarm_notices import FakeReconciliationAlarmNoticeAdapter
from tests.fakes.reconciliation_repository import InMemoryReconciliationRepositoryAdapter
from tests.support.activity import READ_AT
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId(uuid4())
ACCOUNT = uuid4()
OTHER_ACCOUNT = uuid4()
ACCESS = CycleAccess({"wallet": "0xabc"})


class Accounts:
    """The sealed address and the name of the accounts of the tenant, as the accounts context gives them."""

    def sealed_address(self, account_id: UUID) -> SealedAddress:
        return SealedAddress(TENANT, account_id, "Hyperliquid", 1, b"sealed")

    def account_name(self, account_id: UUID) -> str:
        return "test-1" if account_id == ACCOUNT else "test-2"


class Opener:
    def open_cycle_access(self, sealed: SealedAddress) -> CycleAccess:  # noqa: ARG002 - one access for every account
        return ACCESS


class Reader:
    def cycle_reading(self, access: CycleAccess) -> CycleAccount:  # noqa: ARG002 - one reading for every account
        return CycleAccount("USDC", Decimal(1000), ())


class Notices:
    def execute(self, items: Sequence[UnattributableItem]) -> None:
        pass


class Bench:
    def __init__(self) -> None:
        self.store = FlowStore()
        self.readings = InMemoryReconciliationRepositoryAdapter()
        activity = FakeAccountActivityAdapter()
        ledger = InMemoryFlowLedgerAdapter()
        flows = InMemoryFlowRepositoryAdapter(self.store, TENANT)
        accounts = Accounts()
        thresholds = FakeAccountThresholdsAdapter({ACCOUNT: "test-1", OTHER_ACCOUNT: "test-2"})
        record = RecordAccountExecutionsUseCase(flows, activity, InMemoryPlatformOrdersAdapter(), ledger)
        reconcile = ReconcileAccountUseCase(
            flows,
            activity,
            self.readings,
            InMemoryClosedPositionsAdapter(),
            record,
            InMemoryProtectionClosingsAdapter(),
            ReconciliationAlarmPorts(thresholds, thresholds, FakeReconciliationAlarmNoticeAdapter()),
        )
        self.use_case = ReadCycleFlowUseCase(
            flows,
            InMemoryFlowTimingAdapter(self.store, TENANT),
            ReadCycleAccountUseCase(accounts, accounts, Opener(), {"Hyperliquid": Reader()}),
            ReadCycleFlowStateUseCase(
                ReadFlowStateUseCase(
                    flows, activity, ledger, InMemoryExitPlanRepositoryAdapter(ExitPlanStore(), TENANT)
                ),
                ReconcileAccountForCycleUseCase(reconcile, Notices()),
            ),
            self.readings,
        )

    def flow_on(self, account_id: UUID) -> ReadCycleFlowCommand:
        flow = a_flow(
            TENANT, account_id=account_id, status=FlowStatus.ACTIVE, configuration=a_configuration(assets=("BTC",))
        )
        self.store.flows.append(flow)
        return ReadCycleFlowCommand(flow.id, READ_AT, reconciled=False)

    def open_alarm(self, account_id: UUID) -> ReconciliationAlarm:
        alarm = ReconciliationAlarm.of(account_id, BalanceComparison(Decimal(1000), Decimal(980), READ_AT))
        self.readings.open(alarm)
        return alarm


@pytest.fixture
def bench() -> Bench:
    return Bench()


def test_the_flow_carries_the_alarm_open_on_its_account(bench: Bench) -> None:
    command = bench.flow_on(ACCOUNT)
    alarm = bench.open_alarm(ACCOUNT)

    cycle_flow = bench.use_case.execute(command)

    assert cycle_flow.alarm == alarm
    assert cycle_flow.risk_state().openings_suspended == "allarme di riconciliazione sul conto test-1"


def test_an_alarm_on_another_account_does_not_reach_the_flow(bench: Bench) -> None:
    command = bench.flow_on(ACCOUNT)
    bench.open_alarm(OTHER_ACCOUNT)

    assert bench.use_case.execute(command).alarm is None


def test_a_confirmed_alarm_no_longer_suspends_the_openings(bench: Bench) -> None:
    command = bench.flow_on(ACCOUNT)
    bench.open_alarm(ACCOUNT)
    bench.readings.confirm(ACCOUNT, READ_AT + timedelta(hours=1))

    assert bench.use_case.execute(command).alarm is None


def test_the_flow_is_read_with_its_account_and_the_instant_its_cycle_began(bench: Bench) -> None:
    command = bench.flow_on(ACCOUNT)

    cycle_flow = bench.use_case.execute(command)

    assert (cycle_flow.account_name, cycle_flow.exchange, cycle_flow.started_at) == ("test-1", "Hyperliquid", READ_AT)
