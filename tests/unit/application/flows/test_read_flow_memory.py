from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.flows.read_flow_memory import (
    FlowMemoryReading,
    ReadFlowMemoryCommand,
    ReadFlowMemoryUseCase,
)
from autotrading.application.flows.remembered_decisions import MemoryReadings
from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_memory import FlowMemory
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.memory_entry import AssetMemory, MemoryEntry, MemoryOutcome, PastDecision
from autotrading.domain.flows.recorded_decision import DecisionAction, RecordedDecision
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.flow_link import FlowLink
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.order import Order, OrderOrigin, OrderRequest, OrderSource
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.fakes.closed_position_repository import ClosedPositionStore, InMemoryClosedPositionRepositoryAdapter
from tests.fakes.cycles import InMemoryCycleRepositoryAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.order_repository import InMemoryOrderRepositoryAdapter
from tests.fakes.past_decisions import InMemoryPastDecisionsAdapter
from tests.support.activity import CURRENCY, a_position, an_activity
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
        self.closed_positions = ClosedPositionStore()
        self.closings = ReadClosings(self.closed_positions)
        decisions = InMemoryPastDecisionsAdapter(self.cycles, self.orders, self.closed_positions)
        self.use_case = ReadFlowMemoryUseCase(
            InMemoryFlowRepositoryAdapter(self.store, TENANT),
            MemoryReadings(decisions, self.closings),
            self.activity,
            lambda: NOW,
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

    def closed(self, flow: Flow, asset: str, pnl: Decimal) -> None:
        closed_at = NOW - timedelta(hours=1)
        self.closed_positions.positions.append(
            ClosedPosition(
                tenant_id=TENANT,
                flow_id=flow.id,
                asset=asset,
                side=TradeSide.SHORT,
                leverage=2,
                margin=Decimal(50),
                opening=PositionEnd(Decimal(3), closed_at - timedelta(minutes=5)),
                closing=PositionEnd(Decimal(3), closed_at),
                fees=Decimal(0),
                reason=CloseReason.AGENT,
                realized_pnl=pnl,
            )
        )


class ReadClosings(InMemoryClosedPositionRepositoryAdapter):
    """The closed positions of the tenant, counting how many times they were read."""

    def __init__(self, store: ClosedPositionStore) -> None:
        super().__init__(store, TENANT)
        self.reads = 0

    def closed_within(self, flow_id: FlowId, window: TimeWindow) -> list[ClosedPosition]:
        self.reads += 1
        return super().closed_within(flow_id, window)


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

    assert bench.use_case.execute(ReadFlowMemoryCommand(flow.id)) == FlowMemoryReading(active=False, assets=())
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
        PastDecision(planned_at, opening, Decimal(95000), None, position_open=True, opened_at=planned_at),
        MemoryOutcome(Decimal(12), realized=False, course="aperta da 2 ore"),
        160,
    )
    assert memory == FlowMemoryReading(active=True, assets=(AssetMemory("BTC", (entry,)), AssetMemory("ETH", ())))


def test_a_draft_without_an_account_remembers_without_reading_any_position(bench: Bench) -> None:
    flow = bench.flow(FlowMemory(active=True), draft=True)
    closing = RecordedDecision("BTC", DecisionAction.CLOSE, None, 60, "obiettivo")
    planned_at = bench.decided(flow, timedelta(hours=1), closing)

    memory = bench.use_case.execute(ReadFlowMemoryCommand(flow.id))

    assert memory.assets == (
        AssetMemory("BTC", (MemoryEntry.of(PastDecision(planned_at, closing, None, None), None, 160),)),
        AssetMemory("ETH", ()),
    )
    assert bench.activity.read == []


def test_with_the_summary_on_every_asset_begins_with_the_lines_of_its_closings_in_the_currency_of_the_account(
    bench: Bench,
) -> None:
    flow = bench.flow(FlowMemory(active=True, days=2, summary=True, other_assets=True))
    bench.closed(flow, "BTC", Decimal("-2.40"))
    bench.activity.activities[ACCOUNT] = an_activity()

    memory = bench.use_case.execute(ReadFlowMemoryCommand(flow.id))

    line = (
        f"BTC short — oggi: 1 chiuse, 0 vinte, 1 perse, PnL -2,40 {CURRENCY};"
        f" ultimi 2 giorni: 1 chiuse, 0 vinte, 1 perse, PnL -2,40 {CURRENCY}"
    )
    assert memory.assets == (
        AssetMemory("BTC", (), summary=(line,)),
        AssetMemory("ETH", (), other_assets=(line,)),
    )
    assert bench.closings.reads == 1


def test_with_both_options_off_the_closed_positions_are_not_read(bench: Bench) -> None:
    flow = bench.flow(FlowMemory(active=True))
    bench.closed(flow, "BTC", Decimal("-2.40"))
    bench.activity.activities[ACCOUNT] = an_activity()

    memory = bench.use_case.execute(ReadFlowMemoryCommand(flow.id))

    assert memory.assets == (AssetMemory("BTC", ()), AssetMemory("ETH", ()))
    assert bench.closings.reads == 0


def test_a_draft_without_an_account_has_no_summary_and_reads_no_closed_position(bench: Bench) -> None:
    flow = bench.flow(FlowMemory(active=True, summary=True), draft=True)

    memory = bench.use_case.execute(ReadFlowMemoryCommand(flow.id))

    assert memory.assets == (AssetMemory("BTC", ()), AssetMemory("ETH", ()))
    assert bench.closings.reads == 0
