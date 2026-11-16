from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from autotrading.application.flows.guard_flow_loss import GuardFlowLossUseCase
from autotrading.domain.flows.cycle_account import CycleAccount
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.openings_resume import OpeningsResume
from autotrading.domain.flows.openings_suspension import OpeningsStatus, OpeningsSuspension
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.cycles import FakeClockAdapter
from tests.fakes.equity_snapshots import EquitySnapshotStore, InMemoryEquitySnapshotRepositoryAdapter
from tests.fakes.flow_repository import FlowStore
from tests.fakes.openings_suspension import InMemoryOpeningsSuspensionAdapter
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId.new()
FIRST_START = datetime(2026, 11, 10, 9, tzinfo=UTC)
MIDNIGHT = datetime(2026, 11, 16, tzinfo=UTC)
NOW = MIDNIGHT + timedelta(hours=10)
CAPITAL = Decimal(1000)


class World:
    """A flow with its thresholds, its recorded equities, the suspension of its openings and the notices it sent."""

    def __init__(self, resume: OpeningsResume = OpeningsResume.MANUAL, *, thresholds: bool = True) -> None:
        configuration = replace(
            a_configuration(allocated_capital=CAPITAL),
            max_daily_loss_percent=Decimal(5) if thresholds else None,
            max_drawdown_percent=Decimal(10) if thresholds else None,
            openings_resume=resume,
        )
        self.flow = a_flow(TENANT, configuration=configuration)
        self.store = FlowStore()
        self.store.flows.append(self.flow)
        self.equities = InMemoryEquitySnapshotRepositoryAdapter(EquitySnapshotStore(), TENANT)
        self.openings = InMemoryOpeningsSuspensionAdapter(self.store, TENANT)
        self.clock = FakeClockAdapter(NOW)
        self.notices: list[tuple[str, str]] = []
        self.use_case = GuardFlowLossUseCase(self.openings, self.equities, self, self.clock)

    def execute(self, flow_name: str, reason: str) -> None:
        self.notices.append((flow_name, reason))

    def recorded(self, at: datetime, equity: str) -> None:
        realized = Decimal(equity) - CAPITAL
        self.equities.record(
            EquitySnapshot(self.flow.id.value, at, CAPITAL, realized, Decimal(0), Decimal(0), Decimal(0))
        )

    def guarded(self, value: str) -> bool:
        state = FlowState(self.flow.id, "USDC", CAPITAL, (), Decimal(value) - CAPITAL, Decimal(0), Decimal(0))
        account = CycleAccount("USDC", Decimal(5000), ())
        flow = CycleFlow(TENANT, self.flow, "test-1", "Hyperliquid", FIRST_START, account, state)
        suspension = self.use_case.execute(flow)
        assert suspension == self.status.at(NOW, self.flow.configuration.openings_resume).suspension
        return suspension is not None

    @property
    def status(self) -> OpeningsStatus:
        return self.openings.status(self.flow.id.value)


def test_a_loss_beyond_a_threshold_suspends_the_openings_and_tells_the_user_once() -> None:
    world = World()
    world.recorded(MIDNIGHT, "1000")

    assert world.guarded("940")
    assert world.status.suspension == OpeningsSuspension("perdita giornaliera 6% oltre il 5%", NOW)
    assert world.notices == [("alfa", "perdita giornaliera 6% oltre il 5%")]


def test_openings_already_suspended_stay_suspended_without_another_notice() -> None:
    world = World()
    world.recorded(MIDNIGHT, "1000")
    world.guarded("940")

    world.clock.current = NOW + timedelta(minutes=15)

    assert world.guarded("900")
    assert world.status.suspension == OpeningsSuspension("perdita giornaliera 6% oltre il 5%", NOW)
    assert len(world.notices) == 1


def test_losses_within_the_thresholds_suspend_nothing() -> None:
    world = World()
    world.recorded(MIDNIGHT, "1000")

    assert not world.guarded("960")
    assert (world.status.suspension, world.notices) == (None, [])


def test_a_flow_without_thresholds_reads_no_reference() -> None:
    world = World(thresholds=False)
    world.recorded(MIDNIGHT, "1000")

    assert not world.guarded("1")
    assert world.notices == []


def test_the_peak_counts_only_from_the_last_resume_of_the_openings() -> None:
    world = World()
    world.recorded(MIDNIGHT - timedelta(days=2), "1200")
    world.recorded(MIDNIGHT, "1100")
    world.openings.resume(world.flow.id.value, MIDNIGHT - timedelta(days=1))

    assert not world.guarded("1068")


def test_the_peak_counts_from_the_first_start_without_a_resume() -> None:
    world = World()
    world.recorded(FIRST_START - timedelta(days=1), "5000")
    world.recorded(MIDNIGHT - timedelta(days=2), "1200")
    world.recorded(MIDNIGHT, "1100")

    assert world.guarded("1068")
    assert world.notices == [("alfa", "perdita dal picco 11% oltre il 10%")]


def test_a_next_day_suspension_ended_resumes_the_openings_at_midnight_before_the_thresholds() -> None:
    world = World(OpeningsResume.NEXT_DAY)
    world.openings.suspend(world.flow.id.value, OpeningsSuspension("perdita giornaliera 6% oltre il 5%", NOW))
    world.recorded(NOW, "940")
    world.clock.current = MIDNIGHT + timedelta(days=1, minutes=5)

    assert not world.guarded("940")
    assert world.status == OpeningsStatus(None, MIDNIGHT + timedelta(days=1))
    assert world.notices == []


def test_a_manual_suspension_stays_after_midnight() -> None:
    world = World()
    world.openings.suspend(world.flow.id.value, OpeningsSuspension("perdita giornaliera 6% oltre il 5%", NOW))
    world.clock.current = MIDNIGHT + timedelta(days=1, minutes=5)

    assert world.guarded("940")
    assert world.status.suspension is not None
