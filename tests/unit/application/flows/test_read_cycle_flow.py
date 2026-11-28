"""The flow as a cycle reads it at its start, with the alarm of reconciliation of its account (R3.3.1)."""

from collections.abc import Sequence
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.flows.ports import FlowHeldAssets, OpenPositionRecords, ReconciliationAlarmPorts
from autotrading.application.flows.read_cycle_account import ReadCycleAccountUseCase
from autotrading.application.flows.read_cycle_flow import (
    CycleAccountReadings,
    ReadCycleFlowCommand,
    ReadCycleFlowUseCase,
)
from autotrading.application.flows.read_cycle_flow_state import ReadCycleFlowStateUseCase
from autotrading.application.flows.read_flow_state import ReadFlowStateUseCase
from autotrading.application.flows.reconcile_account import ReconcileAccountUseCase
from autotrading.application.flows.reconcile_account_for_cycle import (
    AccountReconciliation,
    AccountReconciliationExclusion,
    ReconcileAccountForCycleUseCase,
)
from autotrading.application.flows.record_account_executions import RecordAccountExecutionsUseCase
from autotrading.domain.flows.account_exposure import AccountExposure, AccountExposureLimit
from autotrading.domain.flows.account_exposure_reading import AccountExposureReading
from autotrading.domain.flows.balance_comparison import BalanceComparison
from autotrading.domain.flows.cycle_access import CycleAccess
from autotrading.domain.flows.cycle_account import CycleAccount, CyclePosition
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
from autotrading.domain.flows.sealed_address import SealedAddress
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.flows.unattributable import UnattributableItem
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.fakes.account_exposure_limits import FakeAccountExposureLimitsAdapter
from tests.fakes.account_thresholds import FakeAccountThresholdsAdapter
from tests.fakes.alert_repository import InMemoryAlertRepositoryAdapter
from tests.fakes.closed_positions import InMemoryClosedPositionsAdapter
from tests.fakes.cycles import InMemoryAccountReconciliationLockAdapter
from tests.fakes.exit_plan_repository import ExitPlanStore, InMemoryExitPlanRepositoryAdapter
from tests.fakes.flow_ledger import InMemoryFlowLedgerAdapter
from tests.fakes.flow_protection_levels import InMemoryFlowProtectionLevelsAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter, InMemoryFlowTimingAdapter
from tests.fakes.platform_orders import InMemoryPlatformOrdersAdapter
from tests.fakes.protection_closings import InMemoryProtectionClosingsAdapter
from tests.fakes.protection_repository import ProtectionStore
from tests.fakes.reconciliation_alarm_notices import FakeReconciliationAlarmNoticeAdapter
from tests.fakes.reconciliation_repository import InMemoryReconciliationRepositoryAdapter
from tests.fakes.waiting_protections import FakeWaitingProtectionsAdapter
from tests.fakes.watched_positions import InMemoryWatchedPositionsAdapter, WatchedPositionStore
from tests.support.activity import READ_AT, a_position, an_activity
from tests.support.closings import closing_readings
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
    def __init__(self) -> None:
        self.positions: tuple[CyclePosition, ...] = ()

    def cycle_reading(self, access: CycleAccess) -> CycleAccount:  # noqa: ARG002 - one reading for every account
        return CycleAccount("USDC", Decimal(1000), self.positions, Decimal(1000))


class Notices:
    def execute(self, items: Sequence[UnattributableItem]) -> None:
        pass


class Bench:
    def __init__(self) -> None:
        self.store = FlowStore()
        self.readings = InMemoryReconciliationRepositoryAdapter()
        self.activity = activity = FakeAccountActivityAdapter()
        self.reader = Reader()
        self.limits = FakeAccountExposureLimitsAdapter({ACCOUNT, OTHER_ACCOUNT})
        protections = ProtectionStore()
        self.waiting = FakeWaitingProtectionsAdapter(protections, TENANT)
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
            ledger,
            InMemoryProtectionClosingsAdapter(),
            ReconciliationAlarmPorts(thresholds, thresholds, FakeReconciliationAlarmNoticeAdapter()),
            InMemoryAlertRepositoryAdapter({}, TENANT),
        )
        self.use_case = ReadCycleFlowUseCase(
            flows,
            InMemoryFlowTimingAdapter(self.store, TENANT),
            CycleAccountReadings(
                ReadCycleAccountUseCase(accounts, accounts, Opener(), {"Hyperliquid": self.reader}),
                self.waiting,
                self.limits,
            ),
            ReadCycleFlowStateUseCase(
                ReadFlowStateUseCase(
                    flows,
                    activity,
                    ledger,
                    OpenPositionRecords(
                        InMemoryExitPlanRepositoryAdapter(ExitPlanStore(), TENANT),
                        InMemoryFlowProtectionLevelsAdapter(protections, TENANT),
                        InMemoryWatchedPositionsAdapter(WatchedPositionStore(), FlowStore(), TENANT),
                    ),
                    closing_readings(TENANT),
                ),
                ReconcileAccountForCycleUseCase(
                    AccountReconciliation(reconcile, Notices()),
                    AccountReconciliationExclusion(flows, InMemoryAccountReconciliationLockAdapter()),
                ),
            ),
            self.readings,
        )

    def flow_on(self, account_id: UUID, *assets: str, account_exposure: bool = False) -> ReadCycleFlowCommand:
        configuration = replace(a_configuration(assets=assets or ("BTC",)), account_exposure_for_agent=account_exposure)
        flow = a_flow(TENANT, account_id=account_id, status=FlowStatus.ACTIVE, configuration=configuration)
        self.store.flows.append(flow)
        return ReadCycleFlowCommand(flow.id, READ_AT, reconciled=False)

    def open_alarm(self, account_id: UUID) -> ReconciliationAlarm:
        alarm = ReconciliationAlarm.of(account_id, BalanceComparison(Decimal(1000), Decimal(980), READ_AT))
        self.readings.open(alarm)
        return alarm

    def hold(self, *assets: str) -> None:
        """Positions on the account, as the exchange shows them to the cycle and to the state of the flow."""
        self.reader.positions = tuple(
            CyclePosition(asset, TradeSide.LONG, Decimal(1), 1, Decimal(100), Decimal(100), Decimal(0), None)
            for asset in assets
        )
        self.activity.activities[ACCOUNT] = an_activity(positions=tuple(a_position(asset) for asset in assets))


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


def test_the_protections_waiting_of_the_positions_are_recorded_before_the_state_is_read(bench: Bench) -> None:
    # R5.5.3: a position opened before the platform recorded its protections shows the stop waiting on the exchange.
    command = bench.flow_on(ACCOUNT)
    bench.hold("BTC")
    bench.waiting.waiting["BTC"] = [(ProtectionKind.STOP_LOSS, Decimal(63000))]

    cycle_flow = bench.use_case.execute(command)

    assert cycle_flow.attributed.exit_plan_of("BTC").stop == Decimal(63000)


def test_only_the_assets_of_the_flow_held_on_the_account_are_asked_for_their_protections(bench: Bench) -> None:
    command = bench.flow_on(ACCOUNT, "BTC", "ETH")
    bench.hold("BTC", "SOL")

    cycle_flow = bench.use_case.execute(command)

    assert bench.waiting.asked == [FlowHeldAssets(ACCOUNT, cycle_flow.flow.id.value, ("BTC",))]


# R5.5.5, ADR controllo-dell-esposizione-del-conto-nel-rischio: the reader shows every position long, of value 100.


def test_without_a_limit_on_the_account_nor_the_option_nothing_of_the_exposure_is_read(bench: Bench) -> None:
    command = bench.flow_on(ACCOUNT, "BTC")
    bench.flow_on(ACCOUNT, "ETH")
    bench.hold("BTC", "ETH")

    cycle_flow = bench.use_case.execute(command)

    assert cycle_flow.account_exposure == AccountExposureReading()
    assert bench.limits.readings == [ACCOUNT]


def test_with_a_limit_the_cycle_reads_it_on_the_balance_with_the_exposure_of_every_flow(bench: Bench) -> None:
    command = bench.flow_on(ACCOUNT, "BTC")
    bench.flow_on(ACCOUNT, "ETH")
    bench.flow_on(OTHER_ACCOUNT, "SOL")
    bench.hold("BTC", "ETH", "SOL")
    bench.limits.limits[ACCOUNT] = Decimal(60)

    reading = bench.use_case.execute(command).account_exposure

    assert reading.limit == AccountExposureLimit(Decimal(60), Decimal(1000), "USDC")
    assert reading.of_account == AccountExposure(Decimal(200), Decimal(0))
    assert reading.of_others is None


def test_with_the_option_the_cycle_reads_the_exposure_of_the_other_flows(bench: Bench) -> None:
    command = bench.flow_on(ACCOUNT, "BTC", account_exposure=True)
    bench.flow_on(ACCOUNT, "ETH")
    bench.hold("BTC", "ETH")

    reading = bench.use_case.execute(command).account_exposure

    assert reading.of_others == AccountExposure(Decimal(100), Decimal(0))
