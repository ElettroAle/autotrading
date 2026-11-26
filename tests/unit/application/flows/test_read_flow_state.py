from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.flows.errors import FlowExchangeUnavailableError, FlowNotFoundError
from autotrading.application.flows.ports import OpenPositionRecords
from autotrading.application.flows.read_flow_state import ReadFlowStateCommand, ReadFlowStateUseCase
from autotrading.domain.flows.capital_change import CapitalChange, CapitalChangeReason
from autotrading.domain.flows.exit_plan import ExitPlan
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.ledger import FlowTotals
from autotrading.domain.flows.trailing_stop import TrailingStop
from autotrading.domain.flows.watched_position import WatchedPosition
from autotrading.domain.orders.client_order_id import ClientOrderId
from autotrading.domain.orders.placed_protection import PlacedProtection
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.fakes.exit_plan_repository import ExitPlanStore, InMemoryExitPlanRepositoryAdapter
from tests.fakes.flow_ledger import InMemoryFlowLedgerAdapter
from tests.fakes.flow_protection_levels import InMemoryFlowProtectionLevelsAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.protection_repository import InMemoryProtectionRepositoryAdapter, ProtectionStore
from tests.fakes.watched_positions import InMemoryWatchedPositionsAdapter, WatchedPositionStore
from tests.support.activity import a_position, an_activity
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId(uuid4())
OFF = TrailingStop()
ACCOUNT = uuid4()


class Bench:
    def __init__(self) -> None:
        self.store = FlowStore()
        self.activity = FakeAccountActivityAdapter()
        self.ledger = InMemoryFlowLedgerAdapter()
        self.exit_plans = InMemoryExitPlanRepositoryAdapter(ExitPlanStore(), TENANT)
        protections = ProtectionStore()
        self.watched = WatchedPositionStore()
        self.protections = InMemoryProtectionRepositoryAdapter(protections, TENANT)
        self.use_case = ReadFlowStateUseCase(
            InMemoryFlowRepositoryAdapter(self.store, TENANT),
            self.activity,
            self.ledger,
            OpenPositionRecords(
                self.exit_plans,
                InMemoryFlowProtectionLevelsAdapter(protections, TENANT),
                InMemoryWatchedPositionsAdapter(self.watched, self.store, TENANT),
            ),
        )

    def flow(self, *assets: str, tenant_id: TenantId = TENANT, trailing: TrailingStop = OFF) -> Flow:
        configuration = replace(a_configuration(assets=assets, allocated_capital=Decimal(500)), trailing_stop=trailing)
        flow = a_flow(tenant_id, account_id=ACCOUNT, configuration=configuration)
        self.store.flows.append(flow)
        return flow

    def protect(self, flow: Flow, asset: str, kind: ProtectionKind, price: int) -> None:
        """A protection the platform placed and recorded for the position of the flow on the asset."""
        self.protections.add(
            PlacedProtection(ACCOUNT, flow.id.value, asset, kind, Decimal(price), "1", ClientOrderId.new())
        )


def change_of(flow: Flow, minutes: int) -> CapitalChange:
    return CapitalChange(
        flow.id,
        datetime(2026, 11, 16, 10, minutes, tzinfo=UTC),
        Decimal(500),
        Decimal(500),
        UserId("anna"),
        CapitalChangeReason.CASH_OUT,
        Decimal(10),
        value_before=Decimal(510),
        cashed_profit=Decimal(10),
    )


@pytest.fixture
def bench() -> Bench:
    return Bench()


def test_the_state_of_a_flow_is_attributed_from_its_account(bench: Bench) -> None:
    alfa, beta = bench.flow("BTC"), bench.flow("ETH")
    bench.ledger.totals[alfa.id] = FlowTotals(alfa.id, Decimal(40), Decimal(2))
    bench.ledger.totals[beta.id] = FlowTotals(beta.id, Decimal(0), Decimal(9))
    bench.activity.activities[ACCOUNT] = an_activity(
        positions=(a_position("BTC", margin=Decimal(100)), a_position("ETH", margin=Decimal(50))),
    )

    state = bench.use_case.execute(ReadFlowStateCommand(alfa.id))

    assert [position.asset for position in state.positions] == ["BTC"]
    assert state.available_liquidity == Decimal(438)


def test_each_open_position_carries_the_exit_plan_in_force(bench: Bench) -> None:
    flow = bench.flow("BTC", "ETH")
    bench.exit_plans.save(flow.id, "BTC", ExitPlan(Decimal(63000), Decimal(58500), "chiusura sotto 59000"))
    bench.protect(flow, "BTC", ProtectionKind.STOP_LOSS, 58500)
    bench.protect(flow, "BTC", ProtectionKind.TAKE_PROFIT, 63000)
    bench.exit_plans.save(flow.id, "ETH", ExitPlan(stop=Decimal(1)))
    bench.activity.activities[ACCOUNT] = an_activity(positions=(a_position("BTC", margin=Decimal(100)),))

    state = bench.use_case.execute(ReadFlowStateCommand(flow.id))

    assert state.exit_plans == {"BTC": ExitPlan(Decimal(63000), Decimal(58500), "chiusura sotto 59000")}


def test_the_stop_and_the_target_are_those_waiting_on_the_exchange_whatever_the_agent_asked(bench: Bench) -> None:
    # R5.5.3: a stop brought within the default of the flow, and a default target the agent never gave.
    flow = bench.flow("BTC")
    bench.exit_plans.save(flow.id, "BTC", ExitPlan(None, Decimal(55000), "chiusura sotto 59000"))
    bench.protect(flow, "BTC", ProtectionKind.STOP_LOSS, 57000)
    bench.protect(flow, "BTC", ProtectionKind.TAKE_PROFIT, 66000)
    bench.activity.activities[ACCOUNT] = an_activity(positions=(a_position("BTC"),))

    state = bench.use_case.execute(ReadFlowStateCommand(flow.id))

    assert state.exit_plan_of("BTC") == ExitPlan(Decimal(66000), Decimal(57000), "chiusura sotto 59000")


def test_a_position_without_a_plan_of_the_agent_shows_the_default_stop_and_no_target(bench: Bench) -> None:
    flow = bench.flow("BTC")
    bench.protect(flow, "BTC", ProtectionKind.STOP_LOSS, 57000)
    bench.activity.activities[ACCOUNT] = an_activity(positions=(a_position("BTC"),))

    state = bench.use_case.execute(ReadFlowStateCommand(flow.id))

    assert state.exit_plan_of("BTC") == ExitPlan(None, Decimal(57000))


def test_a_position_without_protections_recorded_shows_no_level(bench: Bench) -> None:
    flow = bench.flow("BTC")
    bench.exit_plans.save(flow.id, "BTC", ExitPlan(Decimal(63000), Decimal(58500), "chiusura sotto 59000"))
    bench.activity.activities[ACCOUNT] = an_activity(positions=(a_position("BTC"),))

    state = bench.use_case.execute(ReadFlowStateCommand(flow.id))

    assert state.exit_plan_of("BTC") == ExitPlan(None, None, "chiusura sotto 59000")


def test_a_flow_without_anything_in_the_ledger_has_its_capital(bench: Bench) -> None:
    flow = bench.flow("BTC")
    bench.activity.activities[ACCOUNT] = an_activity()

    state = bench.use_case.execute(ReadFlowStateCommand(flow.id))

    assert state.available_liquidity == Decimal(500)


def test_a_flow_of_another_tenant_is_not_found(bench: Bench) -> None:
    other = bench.flow("BTC", tenant_id=TenantId(uuid4()))
    bench.activity.activities[ACCOUNT] = an_activity()

    with pytest.raises(FlowNotFoundError):
        bench.use_case.execute(ReadFlowStateCommand(other.id))


def test_an_unknown_flow_is_not_found(bench: Bench) -> None:
    with pytest.raises(FlowNotFoundError):
        bench.use_case.execute(ReadFlowStateCommand(FlowId.new()))


def test_an_exchange_out_of_reach_is_reported(bench: Bench) -> None:
    flow = bench.flow("BTC")
    bench.activity.activities[ACCOUNT] = an_activity()
    bench.activity.reachable = False

    with pytest.raises(FlowExchangeUnavailableError):
        bench.use_case.execute(ReadFlowStateCommand(flow.id))


def test_the_state_carries_the_changes_of_the_capital_of_the_flow_oldest_first(bench: Bench) -> None:
    # ADR rendimento-composto-tra-le-variazioni-di-capitale: the changes chain the return of the flow.
    flow, other = bench.flow("BTC"), bench.flow("ETH")
    bench.activity.activities[ACCOUNT] = an_activity()
    later, earlier = change_of(flow, minutes=30), change_of(flow, minutes=10)
    bench.store.capital_changes[flow.id] = [later, earlier]
    bench.store.capital_changes[other.id] = [change_of(other, minutes=20)]

    state = bench.use_case.execute(ReadFlowStateCommand(flow.id))

    assert state.capital_changes == (earlier, later)
    assert state.cashed_profit == Decimal(20)


WATCHED = WatchedPosition("BTC", datetime(2026, 11, 26, 9, tzinfo=UTC), Decimal(63000), Decimal(30))


def test_a_position_whose_stop_follows_the_price_carries_the_largest_profit_it_reached(bench: Bench) -> None:
    # R5.5.1, ADR massimo-profitto-raggiunto-nello-stato-della-posizione.
    flow = bench.flow("BTC", "ETH", trailing=TrailingStop(Decimal(2)))
    bench.watched.positions[TENANT, flow.id, "BTC"] = WATCHED
    bench.watched.positions[TENANT, flow.id, "ETH"] = replace(WATCHED, asset="ETH")
    bench.activity.activities[ACCOUNT] = an_activity(positions=(a_position("BTC"),))

    state = bench.use_case.execute(ReadFlowStateCommand(flow.id))

    assert (state.max_profit_of("BTC"), state.max_profit_of("ETH")) == (Decimal(30), None)


def test_the_breakeven_alone_is_enough_for_the_largest_profit_reached(bench: Bench) -> None:
    flow = bench.flow("BTC", trailing=TrailingStop(breakeven_percent=Decimal("1.5")))
    bench.watched.positions[TENANT, flow.id, "BTC"] = WATCHED
    bench.activity.activities[ACCOUNT] = an_activity(positions=(a_position("BTC"),))

    assert bench.use_case.execute(ReadFlowStateCommand(flow.id)).max_profit_of("BTC") == Decimal(30)


def test_a_flow_whose_stop_does_not_follow_the_price_has_no_largest_profit(bench: Bench) -> None:
    flow = bench.flow("BTC")
    bench.watched.positions[TENANT, flow.id, "BTC"] = WATCHED
    bench.activity.activities[ACCOUNT] = an_activity(positions=(a_position("BTC"),))

    state = bench.use_case.execute(ReadFlowStateCommand(flow.id))

    assert state.max_profit_of("BTC") is None
    assert state.watched == {}
