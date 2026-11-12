from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from autotrading.application.flows.errors import FlowNotFoundError
from autotrading.application.flows.list_closed_positions import (
    ListClosedPositionsCommand,
    ListClosedPositionsUseCase,
)
from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.closed_position_repository import ClosedPositionStore, InMemoryClosedPositionRepositoryAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.support.flows import a_flow

OPENED = datetime(2026, 11, 12, 9, tzinfo=UTC)
TENANT = TenantId.new()


def a_position(flow: Flow, closed_after: timedelta) -> ClosedPosition:
    return ClosedPosition(
        tenant_id=flow.tenant_id,
        flow_id=flow.id,
        asset="BTC",
        side=TradeSide.LONG,
        leverage=2,
        margin=Decimal(50),
        opening=PositionEnd(Decimal(100), OPENED),
        closing=PositionEnd(Decimal(101), OPENED + closed_after),
        fees=Decimal(0),
        reason=CloseReason.AGENT,
    )


@pytest.fixture
def flows() -> FlowStore:
    return FlowStore()


@pytest.fixture
def positions() -> ClosedPositionStore:
    return ClosedPositionStore()


def use_case(flows: FlowStore, positions: ClosedPositionStore) -> ListClosedPositionsUseCase:
    return ListClosedPositionsUseCase(
        InMemoryFlowRepositoryAdapter(flows, TENANT), InMemoryClosedPositionRepositoryAdapter(positions, TENANT)
    )


def test_the_closed_positions_come_from_the_most_recent_close(flows: FlowStore, positions: ClosedPositionStore) -> None:
    flow = a_flow(TENANT)
    flows.flows.append(flow)
    hours = (1, 3, 2)
    positions.positions.extend(a_position(flow, timedelta(hours=hour)) for hour in hours)

    found = use_case(flows, positions).execute(ListClosedPositionsCommand(flow.id.value))

    assert [position.closing.at for position in found] == [OPENED + timedelta(hours=hour) for hour in (3, 2, 1)]


def test_the_positions_of_another_flow_stay_out(flows: FlowStore, positions: ClosedPositionStore) -> None:
    flow, other = a_flow(TENANT), a_flow(TENANT, name="beta")
    flows.flows.extend((flow, other))
    positions.positions.extend((a_position(flow, timedelta(hours=1)), a_position(other, timedelta(hours=2))))

    found = use_case(flows, positions).execute(ListClosedPositionsCommand(flow.id.value))

    assert found == [a_position(flow, timedelta(hours=1))]


def test_a_flow_of_another_tenant_does_not_exist(flows: FlowStore, positions: ClosedPositionStore) -> None:
    foreign = a_flow(TenantId.new())
    flows.flows.append(foreign)
    positions.positions.append(replace(a_position(foreign, timedelta(hours=1))))

    with pytest.raises(FlowNotFoundError) as raised:
        use_case(flows, positions).execute(ListClosedPositionsCommand(foreign.id.value))

    assert raised.value.status_code == 404
    assert str(raised.value) == "flusso non trovato"
