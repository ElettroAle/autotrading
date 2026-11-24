from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.flows.read_flow_memory import ReadFlowMemoryCommand, ReadFlowMemoryUseCase
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_memory import FlowMemory
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.memory_entry import AssetMemory, MemoryEntry, MemoryOutcome, PastDecision
from autotrading.domain.flows.recorded_decision import DecisionAction, RecordedDecision
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.flow_link import FlowLink
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.order import Order, OrderOrigin, OrderRequest, OrderSource
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.fakes.closed_position_repository import ClosedPositionStore
from tests.fakes.cycles import InMemoryCycleRepositoryAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.order_repository import InMemoryOrderRepositoryAdapter
from tests.fakes.past_decisions import InMemoryPastDecisionsAdapter
from tests.support.activity import a_position, an_activity
from tests.support.flows import a_configuration, a_flow
from tests.support.orders import EXECUTION

TENANT = TenantId(uuid4())
ACCOUNT = uuid4()
NOW = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)


class Bench:
    def __init__(self) -> None:
        self.store = FlowStore()
        self.activity = FakeAccountActivityAdapter()
        self.cycles = InMemoryCycleRepositoryAdapter()
        self.orders = InMemoryOrderRepositoryAdapter()
        decisions = InMemoryPastDecisionsAdapter(self.cycles, self.orders, ClosedPositionStore())
        self.use_case = ReadFlowMemoryUseCase(
            InMemoryFlowRepositoryAdapter(self.store, TENANT), decisions, self.activity, lambda: NOW
        )

    def flow(self, memory: FlowMemory, *, draft: bool = False) -> Flow:
        configuration = replace(a_configuration(assets=("BTC", "ETH")), memory=memory)
        flow = a_flow(TENANT, account_id=ACCOUNT, configuration=configuration)
        if draft:
            flow = replace(flow, account_id=None, status=FlowStatus.DRAFT)
        self.store.flows.append(flow)
        return flow

    def decided(self, flow: Flow, ago: timedelta, decision: RecordedDecision) -> datetime:
        planned_at = NOW - ago
        self.cycles.record(CycleRecord(flow.id.value, planned_at, CycleOutcome.COMPLETED, decisions=(decision,)))
        return planned_at


def an_opening_executed(flow: Flow, planned_at: datetime, price: Decimal) -> Order:
    market_order = MarketOrder.opening("BTC", Direction.LONG, Decimal("0.0002"), Slippage.default())
    source = OrderSource(OrderOrigin.FLOW, flow=FlowLink(flow.id.value, planned_at, "BTC"))
    request = OrderRequest(ACCOUNT, source, 2, market_order)
    return Order.executed(request, replace(EXECUTION, average_price=price, executed_at=planned_at))


@pytest.fixture
def bench() -> Bench:
    return Bench()


def test_without_the_memory_nothing_is_read_and_there_is_no_memory(bench: Bench) -> None:
    flow = bench.flow(FlowMemory())
    bench.decided(flow, timedelta(hours=1), RecordedDecision("BTC", DecisionAction.CLOSE, None, 60, "obiettivo"))

    assert bench.use_case.execute(ReadFlowMemoryCommand(flow.id)) is None
    assert bench.activity.read == []


def test_the_memory_is_what_the_next_cycle_would_receive_now_with_the_pnl_held_on_the_account(bench: Bench) -> None:
    flow = bench.flow(FlowMemory(active=True, decisions=5, days=14))
    opening = RecordedDecision("BTC", DecisionAction.OPEN, TradeSide.LONG, 80, "rottura")
    planned_at = bench.decided(flow, timedelta(hours=2), opening)
    bench.decided(flow, timedelta(days=20), RecordedDecision("BTC", DecisionAction.CLOSE, None, 60, "vecchia"))
    bench.orders.add(an_opening_executed(flow, planned_at, Decimal(95000)))
    bench.activity.activities[ACCOUNT] = an_activity(positions=(a_position("BTC", unrealized_pnl=Decimal(12)),))

    memory = bench.use_case.execute(ReadFlowMemoryCommand(flow.id))

    entry = MemoryEntry.of(
        PastDecision(planned_at, opening, Decimal(95000), None, position_open=True),
        MemoryOutcome(Decimal(12), realized=False),
    )
    assert memory == (AssetMemory("BTC", (entry,)), AssetMemory("ETH", ()))


def test_a_draft_without_an_account_remembers_without_reading_any_position(bench: Bench) -> None:
    flow = bench.flow(FlowMemory(active=True), draft=True)
    closing = RecordedDecision("BTC", DecisionAction.CLOSE, None, 60, "obiettivo")
    planned_at = bench.decided(flow, timedelta(hours=1), closing)

    memory = bench.use_case.execute(ReadFlowMemoryCommand(flow.id))

    assert memory == (
        AssetMemory("BTC", (MemoryEntry.of(PastDecision(planned_at, closing, None, None), None),)),
        AssetMemory("ETH", ()),
    )
    assert bench.activity.read == []
