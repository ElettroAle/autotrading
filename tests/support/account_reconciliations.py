"""The reconciliation of the accounts of a tenant on adapters in memory, for the periodic check and for the cycle
(Bug 778, ADR riconciliazione-periodica-dei-conti-con-posizioni-aperte)."""

from datetime import timedelta
from uuid import UUID, uuid4

from autotrading.application.flows.ports import ReconciliationAlarmPorts
from autotrading.application.flows.reconcile_account import ReconcileAccountUseCase
from autotrading.application.flows.reconcile_account_for_cycle import (
    AccountReconciliation,
    AccountReconciliationExclusion,
    ReconcileAccountForCycleCommand,
    ReconcileAccountForCycleUseCase,
)
from autotrading.application.flows.reconcile_open_accounts import (
    OpenAccountReadings,
    ReconcileOpenAccountsCommand,
    ReconcileOpenAccountsUseCase,
)
from autotrading.application.flows.record_account_executions import RecordAccountExecutionsUseCase
from autotrading.domain.flows.account_reconciliation import AccountReading
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.fakes.account_reconciliation_intervals import FakeAccountReconciliationIntervalsAdapter
from tests.fakes.account_thresholds import FakeAccountThresholdsAdapter
from tests.fakes.alert_repository import InMemoryAlertRepositoryAdapter
from tests.fakes.closed_positions import InMemoryClosedPositionsAdapter
from tests.fakes.cycles import FakeClockAdapter, InMemoryAccountReconciliationLockAdapter, InMemoryFlowLockAdapter
from tests.fakes.flow_ledger import InMemoryFlowLedgerAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.platform_orders import InMemoryPlatformOrdersAdapter
from tests.fakes.protection_closings import InMemoryProtectionClosingsAdapter
from tests.fakes.protection_repository import ProtectionStore
from tests.fakes.reconciliation_alarm_notices import FakeReconciliationAlarmNoticeAdapter
from tests.fakes.reconciliation_repository import InMemoryReconciliationRepositoryAdapter
from tests.support.activity import READ_AT
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
        self.lock = InMemoryAccountReconciliationLockAdapter()
        # The locks of the cycles of the flows, which the check never takes.
        self.cycles = InMemoryFlowLockAdapter()
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
            AccountReconciliation(reconcile_account, self.notices),
        )
        self.for_cycle = ReconcileAccountForCycleUseCase(
            AccountReconciliation(reconcile_account, self.notices), AccountReconciliationExclusion(flows, self.lock)
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

    def reconcile_for_cycle(self, flow: Flow) -> bool:
        return self.for_cycle.execute(ReconcileAccountForCycleCommand(flow.id))
