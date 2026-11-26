"""The approved orders of a cycle handed to the execution, on the account of the flow (R1.5.5), with the protection
defaults of the version the cycle read (R3.1.2)."""

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from autotrading.application.flows.ports import OpenPositionRecords
from autotrading.application.flows.send_cycle_orders import SendCycleOrdersUseCase
from autotrading.domain.flows.closed_position import PositionEnd
from autotrading.domain.flows.cycle_account import CycleAccount
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.cycle_order import CycleOrder, CycleOrders
from autotrading.domain.flows.exit_plan import ExitPlan, ExitPlanChange
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.protection_defaults import ProtectionDefaults
from autotrading.domain.flows.risk_outcome import ApprovedClose, ApprovedOpening, ApprovedUpdate
from autotrading.domain.flows.stop_outcome import PositionOpening
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.flows.watched_position import TrailingStopNote, WatchedPosition
from autotrading.domain.orders.client_order_id import ClientOrderId
from autotrading.domain.orders.placed_protection import PlacedProtection
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.exit_plan_repository import ExitPlanStore, InMemoryExitPlanRepositoryAdapter
from tests.fakes.flow_protection_levels import InMemoryFlowProtectionLevelsAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.protection_repository import InMemoryProtectionRepositoryAdapter, ProtectionStore
from tests.fakes.watched_positions import InMemoryWatchedPositionsAdapter, WatchedPositionStore
from tests.support.flows import a_configuration, a_flow

PLANNED_AT = datetime(2026, 11, 12, 10, 15, tzinfo=UTC)
TENANT = TenantId.new()
FLOW = a_flow(
    TENANT,
    configuration=replace(
        a_configuration(), assets=("BTC", "ETH"), protection_defaults=ProtectionDefaults.of(Decimal(4), Decimal(9))
    ),
)
STATE = FlowState(FLOW.id, "USDC", Decimal(500), (), Decimal(0), Decimal(0), Decimal(0))
CYCLE_FLOW = CycleFlow(
    TENANT, FLOW, "test-1", "Hyperliquid", PLANNED_AT, CycleAccount("USDC", Decimal(500), (), Decimal(500)), STATE
)


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
        flows = FlowStore()
        flows.flows.append(FLOW)
        self.protections = ProtectionStore()
        self.watched = WatchedPositionStore()
        self.use_case = SendCycleOrdersUseCase(
            self.execution,
            self.openings,
            InMemoryFlowRepositoryAdapter(flows, TENANT),
            OpenPositionRecords(
                self.exit_plans,
                InMemoryFlowProtectionLevelsAdapter(self.protections, TENANT),
                InMemoryWatchedPositionsAdapter(self.watched, flows, TENANT),
            ),
        )

    def protected(self, asset: str, kind: ProtectionKind, price: int) -> None:
        """A protection the execution left waiting on the exchange for the position of the flow."""
        protection = PlacedProtection(
            FLOW.assigned_account_id, FLOW.id.value, asset, kind, Decimal(price), "1", ClientOrderId.new()
        )
        InMemoryProtectionRepositoryAdapter(self.protections, TENANT).add(protection)


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
            FLOW.assigned_account_id,
            FLOW.id.value,
            FLOW.name.value,
            PLANNED_AT,
            (opening, ApprovedClose("ETH")),
            ("BTC", "ETH"),
            Decimal(4),
            Decimal(9),
        )
    ]


def test_a_cycle_without_approved_orders_still_protects_the_positions_with_the_version_in_force() -> None:
    bench = Bench()

    assert bench.use_case.execute(FLOW.id.value, PLANNED_AT, []) == ("inviato",)
    assert bench.execution.cycles == [
        CycleOrders(
            FLOW.assigned_account_id,
            FLOW.id.value,
            FLOW.name.value,
            PLANNED_AT,
            (),
            ("BTC", "ETH"),
            Decimal(4),
            Decimal(9),
        )
    ]


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


def test_an_update_puts_in_force_the_levels_placed_and_its_invalidation() -> None:
    bench = Bench()
    bench.exit_plans.save(FLOW.id, "BTC", PLAN)
    bench.protected("BTC", ProtectionKind.STOP_LOSS, 62000)
    change = ExitPlanChange(stop=Decimal(62000), invalidation="chiusura sotto 61000", remove_target=True)

    bench.use_case.execute(FLOW.id.value, PLANNED_AT, [CycleOrder(CYCLE_FLOW, ApprovedUpdate("BTC", change, ()))])

    assert bench.exit_plans.current(FLOW.id, "BTC") == ExitPlan(None, Decimal(62000), "chiusura sotto 61000")


def test_an_update_the_exchange_refused_leaves_the_levels_in_force() -> None:
    bench = Bench()
    bench.exit_plans.save(FLOW.id, "BTC", PLAN)
    bench.protected("BTC", ProtectionKind.STOP_LOSS, 58500)
    bench.protected("BTC", ProtectionKind.TAKE_PROFIT, 63000)

    bench.use_case.execute(
        FLOW.id.value,
        PLANNED_AT,
        [CycleOrder(CYCLE_FLOW, ApprovedUpdate("BTC", ExitPlanChange(stop=Decimal(62000)), ()))],
    )

    assert bench.exit_plans.current(FLOW.id, "BTC") == PLAN


def test_an_update_of_a_position_without_a_plan_gets_one_from_the_levels_placed() -> None:
    bench = Bench()
    bench.protected("ETH", ProtectionKind.STOP_LOSS, 2850)

    bench.use_case.execute(
        FLOW.id.value,
        PLANNED_AT,
        [CycleOrder(CYCLE_FLOW, ApprovedUpdate("ETH", ExitPlanChange(invalidation="sotto 2900"), ()))],
    )

    assert bench.exit_plans.current(FLOW.id, "ETH") == ExitPlan(None, Decimal(2850), "sotto 2900")


def test_an_update_goes_to_the_execution_with_the_other_orders() -> None:
    bench = Bench()
    update = ApprovedUpdate("BTC", ExitPlanChange(stop=Decimal(62000)), ())

    bench.use_case.execute(FLOW.id.value, PLANNED_AT, [CycleOrder(CYCLE_FLOW, update)])

    assert bench.execution.cycles[0].orders == (update,)


def test_the_cycle_after_a_move_of_the_stop_the_exchange_refused_records_it_once() -> None:
    # R5.5.1, ADR sorveglianza-del-prezzo-per-lo-stop-che-segue.
    bench = Bench()
    refused = WatchedPosition(
        "BTC", PLANNED_AT, Decimal(63000), Decimal(30), "stop BTC non aggiornato, Trigger rejected"
    )
    bench.watched.positions[TENANT, FLOW.id, "BTC"] = refused
    bench.watched.positions[TENANT, FLOW.id, "ETH"] = WatchedPosition("ETH", PLANNED_AT, Decimal(3000), Decimal(0))

    first = bench.use_case.execute(FLOW.id.value, PLANNED_AT, [])
    second = bench.use_case.execute(FLOW.id.value, PLANNED_AT, [])

    assert first == ("inviato", TrailingStopNote("BTC", "stop BTC non aggiornato, Trigger rejected"))
    assert second == ("inviato",)
    assert bench.watched.positions[TENANT, FLOW.id, "BTC"] == refused.told()
