"""The approved orders of a cycle handed to the execution, on the account of the flow (R1.5.5)."""

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from autotrading.application.flows.send_cycle_orders import SendCycleOrdersUseCase
from autotrading.domain.flows.closed_position import PositionEnd
from autotrading.domain.flows.cycle_account import CycleAccount
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.cycle_order import CycleOrder, CycleOrders
from autotrading.domain.flows.exit_plan import ExitPlan
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.risk_outcome import ApprovedClose, ApprovedOpening
from autotrading.domain.flows.stop_outcome import PositionOpening
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.exit_plan_repository import ExitPlanStore, InMemoryExitPlanRepositoryAdapter
from tests.support.flows import a_configuration, a_flow

PLANNED_AT = datetime(2026, 11, 12, 10, 15, tzinfo=UTC)
TENANT = TenantId.new()
FLOW = a_flow(TENANT, configuration=replace(a_configuration(), assets=("BTC", "ETH")))
STATE = FlowState(FLOW.id, "USDC", Decimal(500), (), Decimal(0), Decimal(0), Decimal(0))
CYCLE_FLOW = CycleFlow(TENANT, FLOW, "test-1", "Hyperliquid", PLANNED_AT, CycleAccount("USDC", Decimal(500), ()), STATE)


PLAN = ExitPlan(Decimal(63000), Decimal(58500), "chiusura sotto 59000")


class Execution:
    """The exchange executes the openings it was told to, in the cycle they were sent in."""

    def __init__(self, openings: dict[tuple[FlowId, str], PositionOpening], executed: frozenset[str]) -> None:
        self.cycles: list[CycleOrders] = []
        self._openings = openings
        self._executed = executed

    def execute(self, cycle: CycleOrders) -> Sequence[object]:
        self.cycles.append(cycle)
        for order in cycle.orders:
            if isinstance(order, ApprovedOpening) and order.asset in self._executed:
                end = PositionEnd(Decimal(60000), cycle.planned_at, cycle.planned_at)
                self._openings[FlowId(cycle.flow_id), order.asset] = PositionOpening(
                    order.side, order.leverage, order.margin, end, Decimal(0)
                )
        return ("inviato",)


class KnownOpenings:
    def __init__(self) -> None:
        self.openings: dict[tuple[FlowId, str], PositionOpening] = {}

    def last_opening(self, flow_id: FlowId, asset: str) -> PositionOpening | None:
        return self.openings.get((flow_id, asset))


class Bench:
    def __init__(self, executed: frozenset[str] = frozenset({"BTC"})) -> None:
        self.openings = KnownOpenings()
        self.execution = Execution(self.openings.openings, executed)
        self.store = ExitPlanStore()
        self.exit_plans = InMemoryExitPlanRepositoryAdapter(self.store, TENANT)
        self.use_case = SendCycleOrdersUseCase(self.execution, self.openings, self.exit_plans)


def test_the_orders_go_to_the_account_of_the_flow_with_its_name() -> None:
    bench = Bench()
    execution = bench.execution
    opening = ApprovedOpening("BTC", TradeSide.LONG, Decimal(100), 2, ())

    sent = bench.use_case.execute(
        FLOW.id.value, PLANNED_AT, [CycleOrder(CYCLE_FLOW, opening), CycleOrder(CYCLE_FLOW, ApprovedClose("ETH"))]
    )

    assert sent == ("inviato",)
    assert execution.cycles == [
        CycleOrders(
            FLOW.assigned_account_id, FLOW.id.value, FLOW.name.value, PLANNED_AT, (opening, ApprovedClose("ETH"))
        )
    ]


def test_a_cycle_without_approved_orders_sends_nothing() -> None:
    bench = Bench()

    assert bench.use_case.execute(FLOW.id.value, PLANNED_AT, []) == ()
    assert bench.execution.cycles == []


def test_an_executed_opening_puts_its_exit_plan_in_force() -> None:
    bench = Bench()
    opening = ApprovedOpening("BTC", TradeSide.LONG, Decimal(100), 2, (), PLAN)

    bench.use_case.execute(FLOW.id.value, PLANNED_AT, [CycleOrder(CYCLE_FLOW, opening)])

    assert bench.exit_plans.current(FLOW.id, "BTC") == PLAN


def test_an_executed_opening_without_a_plan_replaces_the_previous_one() -> None:
    bench = Bench()
    bench.exit_plans.save(FLOW.id, "BTC", PLAN)

    bench.use_case.execute(
        FLOW.id.value, PLANNED_AT, [CycleOrder(CYCLE_FLOW, ApprovedOpening("BTC", TradeSide.LONG, Decimal(100), 2, ()))]
    )

    assert bench.exit_plans.current(FLOW.id, "BTC") == ExitPlan()


def test_an_opening_the_exchange_did_not_execute_puts_no_plan_in_force() -> None:
    bench = Bench(executed=frozenset())
    opening = ApprovedOpening("BTC", TradeSide.LONG, Decimal(100), 2, (), PLAN)

    bench.use_case.execute(FLOW.id.value, PLANNED_AT, [CycleOrder(CYCLE_FLOW, opening)])

    assert bench.store.plans == {}


def test_an_opening_of_an_earlier_cycle_is_not_the_one_just_sent() -> None:
    bench = Bench(executed=frozenset())
    earlier = PLANNED_AT.replace(hour=9)
    bench.openings.openings[FLOW.id, "BTC"] = PositionOpening(
        TradeSide.LONG, 2, Decimal(50), PositionEnd(Decimal(60000), earlier, earlier), Decimal(0)
    )
    opening = ApprovedOpening("BTC", TradeSide.LONG, Decimal(100), 2, (), PLAN)

    bench.use_case.execute(FLOW.id.value, PLANNED_AT, [CycleOrder(CYCLE_FLOW, opening)])

    assert bench.store.plans == {}


def test_a_close_puts_no_plan_in_force() -> None:
    bench = Bench()

    bench.use_case.execute(FLOW.id.value, PLANNED_AT, [CycleOrder(CYCLE_FLOW, ApprovedClose("BTC"))])

    assert bench.store.plans == {}
