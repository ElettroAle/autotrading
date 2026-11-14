from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from autotrading.application.flows.errors import FlowNotFoundError
from autotrading.application.flows.read_flow_equity import ReadFlowEquityCommand, ReadFlowEquityUseCase
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.errors import InvalidStatisticsPeriodError
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.equity_snapshots import EquitySnapshotStore, InMemoryEquitySnapshotRepositoryAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.support.flows import a_configuration, a_flow

NOW = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)
TENANT = TenantId.new()


def snapshot(flow: Flow, days_ago: int, equity: int) -> EquitySnapshot:
    return EquitySnapshot(
        flow.id.value,
        NOW - timedelta(days=days_ago),
        Decimal(300),
        Decimal(equity - 300),
        Decimal(0),
        Decimal(0),
        Decimal(0),
    )


@pytest.fixture
def flows() -> FlowStore:
    return FlowStore()


@pytest.fixture
def store() -> EquitySnapshotStore:
    return EquitySnapshotStore()


def a_flow_with_capital(flows: FlowStore, capital: int = 300, tenant_id: TenantId = TENANT) -> Flow:
    flow = a_flow(tenant_id, configuration=replace(a_configuration(), allocated_capital=Decimal(capital)))
    flows.flows.append(flow)
    return flow


def use_case(flows: FlowStore, store: EquitySnapshotStore) -> ReadFlowEquityUseCase:
    return ReadFlowEquityUseCase(
        InMemoryFlowRepositoryAdapter(flows, TENANT),
        InMemoryEquitySnapshotRepositoryAdapter(store, TENANT),
        lambda: NOW,
    )


def recorded(store: EquitySnapshotStore, *snapshots: EquitySnapshot, tenant_id: TenantId = TENANT) -> None:
    adapter = InMemoryEquitySnapshotRepositoryAdapter(store, tenant_id)
    for item in snapshots:
        adapter.record(item)


def test_the_whole_life_of_the_flow_gives_every_cycle_from_the_oldest(
    flows: FlowStore, store: EquitySnapshotStore
) -> None:
    flow = a_flow_with_capital(flows)
    recorded(store, snapshot(flow, 1, 305), snapshot(flow, 3, 310), snapshot(flow, 2, 295))

    equity = use_case(flows, store).execute(ReadFlowEquityCommand(flow.id.value))

    assert [item.equity for item in equity.snapshots] == [Decimal(310), Decimal(295), Decimal(305)]


def test_the_initial_capital_is_the_capital_allocated_to_the_flow(flows: FlowStore, store: EquitySnapshotStore) -> None:
    flow = a_flow_with_capital(flows, capital=450)

    equity = use_case(flows, store).execute(ReadFlowEquityCommand(flow.id.value))

    assert equity.initial_capital == Decimal(450)


def test_the_last_30_days_leave_the_older_cycles_out(flows: FlowStore, store: EquitySnapshotStore) -> None:
    flow = a_flow_with_capital(flows)
    recorded(store, *(snapshot(flow, days, 300 + days) for days in (59, 31, 29, 1)))

    equity = use_case(flows, store).execute(ReadFlowEquityCommand(flow.id.value, "30d"))

    assert [item.planned_at for item in equity.snapshots] == [NOW - timedelta(days=29), NOW - timedelta(days=1)]


def test_a_range_gives_the_cycles_between_its_bounds(flows: FlowStore, store: EquitySnapshotStore) -> None:
    flow = a_flow_with_capital(flows)
    recorded(store, *(snapshot(flow, days, 300 + days) for days in (5, 4, 3, 2)))
    first, last = (NOW - timedelta(days=4)).date(), (NOW - timedelta(days=3)).date()
    command = ReadFlowEquityCommand(flow.id.value, "range", first, last)

    equity = use_case(flows, store).execute(command)

    assert [item.equity for item in equity.snapshots] == [Decimal(304), Decimal(303)]


def test_a_flow_without_cycles_has_no_point(flows: FlowStore, store: EquitySnapshotStore) -> None:
    flow = a_flow_with_capital(flows)

    assert use_case(flows, store).execute(ReadFlowEquityCommand(flow.id.value)).snapshots == ()


def test_a_flow_of_another_tenant_is_not_found(flows: FlowStore, store: EquitySnapshotStore) -> None:
    other = a_flow_with_capital(flows, tenant_id=TenantId.new())
    recorded(store, snapshot(other, 1, 305), tenant_id=other.tenant_id)

    with pytest.raises(FlowNotFoundError):
        use_case(flows, store).execute(ReadFlowEquityCommand(other.id.value))


def test_an_unknown_flow_is_not_found(flows: FlowStore, store: EquitySnapshotStore) -> None:
    with pytest.raises(FlowNotFoundError):
        use_case(flows, store).execute(ReadFlowEquityCommand(FlowId.new().value))


def test_an_incomplete_range_is_refused_before_reading(flows: FlowStore, store: EquitySnapshotStore) -> None:
    with pytest.raises(InvalidStatisticsPeriodError):
        use_case(flows, store).execute(ReadFlowEquityCommand(FlowId.new().value, "range"))
