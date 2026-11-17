"""The suspension of the openings of a flow in force now, whatever its cause (R3.2.2, R3.3.1, R3.3.2)."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from autotrading.application.flows.errors import FlowNotFoundError
from autotrading.application.flows.read_openings_suspension import (
    ReadOpeningsSuspensionCommand,
    ReadOpeningsSuspensionUseCase,
)
from autotrading.domain.flows.balance_comparison import BalanceComparison
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.openings_resume import OpeningsResume
from autotrading.domain.flows.openings_suspension import OpeningsSuspension, OpeningsSuspensionCause
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_thresholds import FakeAccountThresholdsAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.openings_suspension import InMemoryOpeningsSuspensionAdapter
from tests.fakes.reconciliation_repository import InMemoryReconciliationRepositoryAdapter
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId.new()
SUSPENDED_AT = datetime(2026, 11, 16, 10, tzinfo=UTC)
NEXT_MIDNIGHT = datetime(2026, 11, 17, tzinfo=UTC)
LOSS = OpeningsSuspension("perdita giornaliera 6% oltre il 5%", SUSPENDED_AT)


class Bench:
    def __init__(self) -> None:
        self.store = FlowStore()
        self.readings = InMemoryReconciliationRepositoryAdapter()
        self.accounts = FakeAccountThresholdsAdapter({})
        self.openings = InMemoryOpeningsSuspensionAdapter(self.store, TENANT)
        self.now = SUSPENDED_AT + timedelta(hours=1)
        self.use_case = ReadOpeningsSuspensionUseCase(
            InMemoryFlowRepositoryAdapter(self.store, TENANT),
            self.openings,
            self.readings,
            self.accounts,
            lambda: self.now,
        )

    def flow_on(self, account_name: str, resume: OpeningsResume = OpeningsResume.MANUAL) -> Flow:
        flow = a_flow(TENANT, configuration=replace(a_configuration(), openings_resume=resume))
        self.store.flows.append(flow)
        self.accounts.names[flow.assigned_account_id] = account_name
        return flow

    def alarm_on(self, flow: Flow) -> ReconciliationAlarm:
        comparison = BalanceComparison(Decimal(1000), Decimal(980), SUSPENDED_AT)
        alarm = ReconciliationAlarm.of(flow.assigned_account_id, comparison)
        self.readings.open(alarm)
        return alarm

    def loss_on(self, flow: Flow) -> None:
        self.openings.suspend(flow.id.value, LOSS)

    def suspension(self, flow: Flow) -> OpeningsSuspension | None:
        return self.use_case.execute(ReadOpeningsSuspensionCommand(flow.id))


@pytest.fixture
def bench() -> Bench:
    return Bench()


def test_an_open_alarm_on_the_account_suspends_the_openings_with_its_reason(bench: Bench) -> None:
    flow = bench.flow_on("test-1")
    bench.alarm_on(flow)

    suspension = bench.suspension(flow)

    assert suspension == OpeningsSuspension(
        "allarme di riconciliazione sul conto test-1", SUSPENDED_AT, OpeningsSuspensionCause.RECONCILIATION
    )
    assert suspension is not None
    assert not suspension.resumable


def test_without_any_cause_the_openings_are_not_suspended(bench: Bench) -> None:
    assert bench.suspension(bench.flow_on("test-1")) is None


def test_a_confirmed_alarm_no_longer_suspends_the_openings(bench: Bench) -> None:
    flow = bench.flow_on("test-1")
    bench.alarm_on(flow)
    bench.readings.confirm(flow.assigned_account_id, SUSPENDED_AT)

    assert bench.suspension(flow) is None


def test_the_maximum_loss_in_force_is_read_with_its_reason_and_instant(bench: Bench) -> None:
    flow = bench.flow_on("test-1")
    bench.loss_on(flow)

    suspension = bench.suspension(flow)

    assert suspension == LOSS
    assert suspension is not None
    assert suspension.resumable


def test_the_maximum_loss_comes_before_the_alarm_since_the_user_can_resume_it(bench: Bench) -> None:
    flow = bench.flow_on("test-1")
    bench.alarm_on(flow)
    bench.loss_on(flow)

    assert bench.suspension(flow) == LOSS


def test_a_next_day_loss_reads_lifted_from_the_next_midnight(bench: Bench) -> None:
    flow = bench.flow_on("test-1", OpeningsResume.NEXT_DAY)
    bench.loss_on(flow)

    bench.now = NEXT_MIDNIGHT

    assert bench.suspension(flow) is None


def test_a_manual_loss_reads_in_force_after_midnight(bench: Bench) -> None:
    flow = bench.flow_on("test-1")
    bench.loss_on(flow)

    bench.now = NEXT_MIDNIGHT

    assert bench.suspension(flow) == LOSS


def test_a_flow_of_another_tenant_is_not_found(bench: Bench) -> None:
    with pytest.raises(FlowNotFoundError):
        bench.use_case.execute(ReadOpeningsSuspensionCommand(FlowId.new()))
