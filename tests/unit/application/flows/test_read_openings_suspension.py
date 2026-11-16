"""Why the openings of a flow are suspended, as the page of the flow tells it (R3.3.2)."""

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
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_thresholds import FakeAccountThresholdsAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.reconciliation_repository import InMemoryReconciliationRepositoryAdapter
from tests.support.activity import READ_AT
from tests.support.flows import a_flow

TENANT = TenantId.new()


class Bench:
    def __init__(self) -> None:
        self.store = FlowStore()
        self.readings = InMemoryReconciliationRepositoryAdapter()
        self.accounts = FakeAccountThresholdsAdapter({})
        self.use_case = ReadOpeningsSuspensionUseCase(
            InMemoryFlowRepositoryAdapter(self.store, TENANT), self.readings, self.accounts
        )

    def flow_on(self, account_name: str) -> Flow:
        flow = a_flow(TENANT)
        self.store.flows.append(flow)
        self.accounts.names[flow.assigned_account_id] = account_name
        return flow

    def alarm_on(self, flow: Flow) -> ReconciliationAlarm:
        comparison = BalanceComparison(Decimal(1000), Decimal(980), READ_AT)
        alarm = ReconciliationAlarm.of(flow.assigned_account_id, comparison)
        self.readings.open(alarm)
        return alarm


@pytest.fixture
def bench() -> Bench:
    return Bench()


def test_an_open_alarm_on_the_account_suspends_the_openings_with_its_reason(bench: Bench) -> None:
    flow = bench.flow_on("test-1")
    bench.alarm_on(flow)

    reason = bench.use_case.execute(ReadOpeningsSuspensionCommand(flow.id))

    assert reason == "allarme di riconciliazione sul conto test-1"


def test_without_an_open_alarm_the_openings_are_not_suspended(bench: Bench) -> None:
    flow = bench.flow_on("test-1")

    assert bench.use_case.execute(ReadOpeningsSuspensionCommand(flow.id)) is None


def test_a_confirmed_alarm_no_longer_suspends_the_openings(bench: Bench) -> None:
    flow = bench.flow_on("test-1")
    bench.alarm_on(flow)
    bench.readings.confirm(flow.assigned_account_id, READ_AT)

    assert bench.use_case.execute(ReadOpeningsSuspensionCommand(flow.id)) is None


def test_a_flow_of_another_tenant_is_not_found(bench: Bench) -> None:
    with pytest.raises(FlowNotFoundError):
        bench.use_case.execute(ReadOpeningsSuspensionCommand(FlowId.new()))
