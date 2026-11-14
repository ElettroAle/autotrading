from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from autotrading.application.flows.errors import FlowNotFoundError
from autotrading.application.flows.read_flow_statistics import ReadFlowStatisticsCommand, ReadFlowStatisticsUseCase
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.errors import InvalidStatisticsPeriodError
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.closed_position_repository import ClosedPositionStore, InMemoryClosedPositionRepositoryAdapter
from tests.fakes.cycles import InMemoryCycleHistoryAdapter, InMemoryCycleRepositoryAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.support.flows import a_flow

NOW = datetime(2026, 11, 14, 12, tzinfo=UTC)
TENANT = TenantId.new()


class Platform:
    def __init__(self) -> None:
        self.flows = FlowStore()
        self.positions = ClosedPositionStore()
        self.cycles = InMemoryCycleRepositoryAdapter()

    def flow(self, tenant_id: TenantId = TENANT) -> Flow:
        flow = a_flow(tenant_id)
        self.flows.flows.append(flow)
        return flow

    def close(self, flow: Flow, net_pnl: str, closed_at: datetime, fees: str = "0") -> None:
        self.positions.positions.append(
            ClosedPosition(
                tenant_id=flow.tenant_id,
                flow_id=flow.id,
                asset="BTC",
                side=TradeSide.LONG,
                leverage=2,
                margin=Decimal(50),
                opening=PositionEnd(Decimal(100), closed_at - timedelta(hours=1)),
                closing=PositionEnd(Decimal(100), closed_at),
                fees=Decimal(fees),
                reason=CloseReason.AGENT,
                realized_pnl=Decimal(net_pnl) + Decimal(fees),
            )
        )

    def call_model(self, flow: Flow, cost: str, planned_at: datetime) -> None:
        call = CallCost(10, 10, Decimal(cost))
        self.cycles.record(CycleRecord(flow.id.value, planned_at, CycleOutcome.COMPLETED, cost=call))

    def use_case(self) -> ReadFlowStatisticsUseCase:
        return ReadFlowStatisticsUseCase(
            InMemoryFlowRepositoryAdapter(self.flows, TENANT),
            InMemoryClosedPositionRepositoryAdapter(self.positions, TENANT),
            InMemoryCycleHistoryAdapter(self.cycles, self.flows, TENANT),
            lambda: NOW,
        )


@pytest.fixture
def platform() -> Platform:
    return Platform()


def test_the_statistics_of_the_whole_life_count_every_closed_position_and_every_call(platform: Platform) -> None:
    flow = platform.flow()
    platform.close(flow, "20", NOW - timedelta(days=40), fees="1")
    platform.close(flow, "-4", NOW - timedelta(days=1), fees="2")
    platform.call_model(flow, "1.00", NOW - timedelta(days=40))
    platform.call_model(flow, "0.20", NOW - timedelta(days=1))

    statistics = platform.use_case().execute(ReadFlowStatisticsCommand(flow.id.value))

    assert (statistics.won, statistics.lost, statistics.operations) == (1, 1, 2)
    assert statistics.total_fees == Decimal(3)
    assert statistics.model_cost_usd == Decimal("1.20")


def test_the_last_7_days_leave_out_what_happened_before(platform: Platform) -> None:
    flow = platform.flow()
    platform.close(flow, "20", NOW - timedelta(days=8))
    platform.close(flow, "-4", NOW - timedelta(days=6))
    platform.call_model(flow, "1.00", NOW - timedelta(days=8))
    platform.call_model(flow, "0.20", NOW - timedelta(days=6))

    statistics = platform.use_case().execute(ReadFlowStatisticsCommand(flow.id.value, "7d"))

    assert (statistics.won, statistics.lost, statistics.operations) == (0, 1, 1)
    assert statistics.model_cost_usd == Decimal("0.20")


def test_a_range_holds_its_first_and_last_day(platform: Platform) -> None:
    flow = platform.flow()
    for day in (9, 10, 12, 13):
        platform.close(flow, "1", datetime(2026, 11, day, 23, 59, tzinfo=UTC))

    command = ReadFlowStatisticsCommand(flow.id.value, "range", date(2026, 11, 10), date(2026, 11, 12))
    statistics = platform.use_case().execute(command)

    assert statistics.operations == 2


def test_the_positions_and_the_calls_of_another_flow_do_not_count(platform: Platform) -> None:
    flow, other = platform.flow(), platform.flow()
    platform.close(other, "20", NOW - timedelta(days=1))
    platform.call_model(other, "1.00", NOW - timedelta(days=1))

    statistics = platform.use_case().execute(ReadFlowStatisticsCommand(flow.id.value))

    assert statistics.operations == 0
    assert statistics.win_rate_percent is None
    assert statistics.model_cost_usd == Decimal(0)


def test_a_flow_of_another_tenant_does_not_exist(platform: Platform) -> None:
    other = platform.flow(TenantId.new())

    with pytest.raises(FlowNotFoundError):
        platform.use_case().execute(ReadFlowStatisticsCommand(other.id.value))


def test_an_invalid_period_is_rejected_before_reading_the_flow(platform: Platform) -> None:
    other = platform.flow(TenantId.new())

    with pytest.raises(InvalidStatisticsPeriodError):
        platform.use_case().execute(ReadFlowStatisticsCommand(other.id.value, "1y"))
