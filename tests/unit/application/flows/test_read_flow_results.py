"""The results of a flow over the period the user chooses (R6.4.2, ADR riepilogo-dei-risultati-nell-api)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from autotrading.application.flows.errors import FlowNotFoundError
from autotrading.application.flows.ports import OpenPositionRecords
from autotrading.application.flows.read_flow_results import (
    FlowPeriodPorts,
    ReadFlowResultsCommand,
    ReadFlowResultsUseCase,
)
from autotrading.application.flows.read_flow_state import ReadFlowStateUseCase
from autotrading.application.flows.read_next_cycle import ReadNextCycleUseCase
from autotrading.application.flows.read_openings_suspension import ReadOpeningsSuspensionUseCase
from autotrading.domain.flows.balance_comparison import BalanceComparison
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.errors import InvalidStatisticsPeriodError
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.ledger import FlowTotals
from autotrading.domain.flows.openings_suspension import OpeningsSuspension, OpeningsSuspensionCause
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.fakes.account_thresholds import FakeAccountThresholdsAdapter
from tests.fakes.cycles import InMemoryCycleHistoryAdapter, InMemoryCycleRepositoryAdapter
from tests.fakes.equity_snapshots import EquitySnapshotStore, InMemoryEquitySnapshotRepositoryAdapter
from tests.fakes.exit_plan_repository import ExitPlanStore, InMemoryExitPlanRepositoryAdapter
from tests.fakes.flow_ledger import InMemoryFlowLedgerAdapter
from tests.fakes.flow_protection_levels import InMemoryFlowProtectionLevelsAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter, InMemoryFlowTimingAdapter
from tests.fakes.openings_suspension import InMemoryOpeningsSuspensionAdapter
from tests.fakes.protection_repository import ProtectionStore
from tests.fakes.reconciliation_repository import InMemoryReconciliationRepositoryAdapter
from tests.fakes.watched_positions import InMemoryWatchedPositionsAdapter, WatchedPositionStore
from tests.support.activity import CURRENCY, a_position, an_activity
from tests.support.flows import a_configuration, a_flow

NOW = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)
TENANT = TenantId.new()


class Bench:
    def __init__(self) -> None:
        self.store = FlowStore()
        self.activity = FakeAccountActivityAdapter()
        self.ledger = InMemoryFlowLedgerAdapter()
        self.cycles = InMemoryCycleRepositoryAdapter()
        self.equity = EquitySnapshotStore()
        self.readings = InMemoryReconciliationRepositoryAdapter()
        self.accounts = FakeAccountThresholdsAdapter({})
        flows = InMemoryFlowRepositoryAdapter(self.store, TENANT)
        self.use_case = ReadFlowResultsUseCase(
            ReadFlowStateUseCase(
                flows,
                self.activity,
                self.ledger,
                OpenPositionRecords(
                    InMemoryExitPlanRepositoryAdapter(ExitPlanStore(), TENANT),
                    InMemoryFlowProtectionLevelsAdapter(ProtectionStore(), TENANT),
                    InMemoryWatchedPositionsAdapter(WatchedPositionStore(), FlowStore(), TENANT),
                ),
            ),
            ReadOpeningsSuspensionUseCase(
                flows, InMemoryOpeningsSuspensionAdapter(self.store, TENANT), self.readings, self.accounts, lambda: NOW
            ),
            ReadNextCycleUseCase(flows, InMemoryFlowTimingAdapter(self.store, TENANT), lambda: NOW),
            FlowPeriodPorts(
                InMemoryEquitySnapshotRepositoryAdapter(self.equity, TENANT),
                InMemoryCycleHistoryAdapter(self.cycles, self.store, TENANT),
            ),
            lambda: NOW,
        )

    def flow(self, status: FlowStatus = FlowStatus.STOPPED) -> Flow:
        flow = a_flow(
            TENANT, status=status, configuration=a_configuration(assets=("BTC",), allocated_capital=Decimal(100))
        )
        self.store.flows.append(flow)
        self.store.anchors[flow.id] = NOW - timedelta(minutes=5)
        self.activity.activities[flow.assigned_account_id] = an_activity()
        self.accounts.names[flow.assigned_account_id] = "test-1"
        return flow

    def equity_at(self, flow: Flow, days_ago: int, equity: str) -> None:
        snapshot = EquitySnapshot(
            flow.id.value,
            NOW - timedelta(days=days_ago),
            Decimal(100),
            Decimal(equity) - Decimal(100),
            Decimal(0),
            Decimal(0),
            Decimal(0),
        )
        InMemoryEquitySnapshotRepositoryAdapter(self.equity, TENANT).record(snapshot)

    def cycle(self, flow: Flow, days_ago: int, outcome: CycleOutcome) -> None:
        self.cycles.record(CycleRecord(flow.id.value, NOW - timedelta(days=days_ago), outcome))


@pytest.fixture
def bench() -> Bench:
    return Bench()


def test_the_results_measure_the_gain_in_all_from_the_state_of_the_flow(bench: Bench) -> None:
    flow = bench.flow()
    bench.ledger.totals[flow.id] = FlowTotals(flow.id, Decimal("2.5"), Decimal(0))

    results = bench.use_case.execute(ReadFlowResultsCommand(flow.id.value))

    assert (results.total_gain, results.total_gain_percent, results.currency) == (
        Decimal("2.5"),
        Decimal("2.50"),
        CURRENCY,
    )


def test_the_gain_in_the_period_reads_only_the_equity_recorded_in_the_period(bench: Bench) -> None:
    flow = bench.flow()
    bench.equity_at(flow, 9, "100.5")
    bench.equity_at(flow, 6, "102.1")
    bench.equity_at(flow, 1, "102.5")

    results = bench.use_case.execute(ReadFlowResultsCommand(flow.id.value, "7d"))

    assert (results.period_gain, results.period_gain_percent) == (Decimal("0.4"), Decimal("0.40"))


def test_the_gain_in_all_reads_the_equity_up_to_now_included(bench: Bench) -> None:
    # ADR indice-delle-previsioni-in-attesa-e-patrimonio-con-limite-superiore: the read is bounded by the clock.
    flow = bench.flow()
    bench.equity_at(flow, 1, "100.5")
    bench.equity_at(flow, 0, "101")
    bench.equity_at(flow, -1, "150")

    results = bench.use_case.execute(ReadFlowResultsCommand(flow.id.value))

    assert results.period_gain == Decimal("0.5")


def test_the_failed_cycles_are_counted_only_in_the_period(bench: Bench) -> None:
    flow = bench.flow()
    bench.cycle(flow, 10, CycleOutcome.FAILED)
    bench.cycle(flow, 3, CycleOutcome.FAILED)
    bench.cycle(flow, 2, CycleOutcome.COMPLETED)
    bench.cycle(flow, 1, CycleOutcome.FAILED)

    results = bench.use_case.execute(ReadFlowResultsCommand(flow.id.value, "7d"))

    assert results.failed_cycles == 2


def test_the_open_positions_are_those_of_the_flow_on_the_account(bench: Bench) -> None:
    flow = bench.flow()
    bench.activity.activities[flow.assigned_account_id] = an_activity(positions=(a_position("BTC"), a_position("ETH")))

    results = bench.use_case.execute(ReadFlowResultsCommand(flow.id.value))

    assert results.open_positions == 1


def test_a_range_reads_its_days(bench: Bench) -> None:
    flow = bench.flow()
    bench.cycle(flow, 3, CycleOutcome.FAILED)
    bench.cycle(flow, 1, CycleOutcome.FAILED)
    instant = NOW - timedelta(days=3)

    results = bench.use_case.execute(ReadFlowResultsCommand(flow.id.value, "range", instant, instant))

    assert results.failed_cycles == 1


def test_a_period_the_user_cannot_have_meant_is_refused_before_reading_the_exchange(bench: Bench) -> None:
    flow = bench.flow()
    bench.activity.reachable = False

    with pytest.raises(InvalidStatisticsPeriodError):
        bench.use_case.execute(ReadFlowResultsCommand(flow.id.value, "1y"))


def test_a_flow_of_another_tenant_is_not_found(bench: Bench) -> None:
    with pytest.raises(FlowNotFoundError):
        bench.use_case.execute(ReadFlowResultsCommand(FlowId.new().value))


def test_the_results_tell_why_the_openings_are_suspended_by_an_alarm_on_the_account(bench: Bench) -> None:
    flow = bench.flow()
    comparison = BalanceComparison(Decimal(1000), Decimal(980), NOW)
    bench.readings.open(ReconciliationAlarm.of(flow.assigned_account_id, comparison))

    results = bench.use_case.execute(ReadFlowResultsCommand(flow.id.value))

    assert results.openings_suspension == OpeningsSuspension(
        "allarme di riconciliazione sul conto test-1", NOW, OpeningsSuspensionCause.RECONCILIATION
    )


def test_the_openings_of_a_flow_whose_account_has_no_alarm_are_not_suspended(bench: Bench) -> None:
    flow = bench.flow()

    assert bench.use_case.execute(ReadFlowResultsCommand(flow.id.value)).openings_suspension is None


def test_the_results_of_an_active_flow_tell_when_its_next_cycle_falls(bench: Bench) -> None:
    flow = bench.flow(FlowStatus.ACTIVE)

    results = bench.use_case.execute(ReadFlowResultsCommand(flow.id.value))

    assert results.next_cycle_at == NOW + timedelta(minutes=10)


@pytest.mark.parametrize("status", [FlowStatus.PAUSED, FlowStatus.STOPPED])
def test_the_results_of_a_flow_that_is_not_active_have_no_next_cycle(bench: Bench, status: FlowStatus) -> None:
    flow = bench.flow(status)

    assert bench.use_case.execute(ReadFlowResultsCommand(flow.id.value)).next_cycle_at is None


def test_the_next_cycle_does_not_depend_on_the_period(bench: Bench) -> None:
    flow = bench.flow(FlowStatus.ACTIVE)

    results = bench.use_case.execute(ReadFlowResultsCommand(flow.id.value, "7d"))

    assert results.next_cycle_at == NOW + timedelta(minutes=10)
