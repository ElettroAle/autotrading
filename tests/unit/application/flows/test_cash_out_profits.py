"""ADR incasso-dei-profitti: the cash-out of the profits of a flow, on the use cases with fake adapters."""

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.flows.cash_out_profits import CashOutPorts, CashOutProfitsCommand, CashOutProfitsUseCase
from autotrading.application.flows.close_flow_positions import CloseFlowPositionsUseCase, ClosingPorts
from autotrading.application.flows.errors import FlowNotFoundError
from autotrading.application.flows.ports import PositionToClose
from autotrading.application.flows.read_flow_state import ReadFlowStateUseCase
from autotrading.application.flows.record_account_executions import RecordAccountExecutionsUseCase
from autotrading.domain.flows.capital_change import CapitalChange, CapitalChangeReason
from autotrading.domain.flows.closed_position import CloseReason, PositionEnd
from autotrading.domain.flows.errors import (
    ArchivedFlowNotModifiableError,
    CashOutCapitalOutOfRangeError,
    FlowWithoutProfitsError,
)
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.stop_outcome import ClosingFill, PositionLeftOpen, PositionOpening
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.fakes.cash_out_notices import FakeCashOutNoticeAdapter
from tests.fakes.closed_position_repository import ClosedPositionStore, InMemoryClosedPositionRepositoryAdapter
from tests.fakes.exit_plan_repository import ExitPlanStore, InMemoryExitPlanRepositoryAdapter
from tests.fakes.flow_ledger import InMemoryFlowLedgerAdapter
from tests.fakes.flow_protection_levels import InMemoryFlowProtectionLevelsAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.ledger_recording import FakeLedgerRecordingAdapter
from tests.fakes.platform_orders import InMemoryPlatformOrdersAdapter
from tests.fakes.position_closed_notices import FakePositionClosedNoticeAdapter
from tests.fakes.protection_repository import ProtectionStore
from tests.support.activity import a_fill, a_position, an_activity
from tests.support.flows import a_configuration, a_flow
from tests.support.position_closings import NOTHING_TO_CLOSE, ClosingAnswer, closed_by, refused

USER = UserId("oid-anna")
NOW = datetime(2026, 11, 16, 9, 30, tzinfo=UTC)
CLOSED_AT = datetime(2026, 11, 16, 9, 29, tzinfo=UTC)
OPENED = datetime(2026, 11, 16, 8, 0, tzinfo=UTC)
OPENING = PositionOpening(TradeSide.LONG, 1, Decimal(100), PositionEnd(Decimal(100), OPENED), Decimal(0))


class Exchange:
    """Closes the positions the account shows: each closing executes with the PnL it had, less its fee."""

    def __init__(self, activity: FakeAccountActivityAdapter) -> None:
        self.activity = activity
        self.refusals: dict[str, str] = {}
        self.fee = Decimal(2)
        self.closed: list[str] = []

    def execute(self, position: PositionToClose) -> ClosingAnswer:
        if position.asset in self.refusals:
            return refused(self.refusals[position.asset])
        reading = self.activity.activities[position.account_id]
        held = next((each for each in reading.positions if each.asset == position.asset), None)
        if held is None:
            return NOTHING_TO_CLOSE
        self.closed.append(position.asset)
        remaining = tuple(each for each in reading.positions if each.asset != position.asset)
        self.activity.activities[position.account_id] = replace(reading, positions=remaining)
        execution = a_fill(
            position.asset,
            None,
            realized_pnl=held.unrealized_pnl,
            fee=self.fee,
            size=-held.size,
            start_position=held.size,
            executed_at=CLOSED_AT,
        )
        self.activity.executions.setdefault(position.account_id, []).append(execution)
        return closed_by(ClosingFill(Decimal(110), CLOSED_AT, self.fee, held.unrealized_pnl))


class Openings:
    """The flow opened every position it holds, with the same order."""

    def __init__(self) -> None:
        self.asked: list[tuple[FlowId, str]] = []

    def last_opening(self, flow_id: FlowId, asset: str) -> PositionOpening | None:
        self.asked.append((flow_id, asset))
        return OPENING


class Cycles:
    def __init__(self) -> None:
        self.waited: list[FlowId] = []

    def wait_until_finished(self, flow_id: FlowId) -> None:
        self.waited.append(flow_id)


class Bench:
    def __init__(self) -> None:
        self.tenant_id = TenantId.new()
        self.account_id = uuid4()
        self.store = FlowStore()
        self.flows = InMemoryFlowRepositoryAdapter(self.store, self.tenant_id)
        self.activity = FakeAccountActivityAdapter()
        self.activity.activities[self.account_id] = an_activity()
        self.ledger = InMemoryFlowLedgerAdapter()
        self.exchange = Exchange(self.activity)
        self.cycles = Cycles()
        self.closed = ClosedPositionStore()
        self.exit_plans = InMemoryExitPlanRepositoryAdapter(ExitPlanStore(), self.tenant_id)
        closings = CloseFlowPositionsUseCase(
            ClosingPorts(
                self.cycles,
                self.exchange,
                Openings(),
                InMemoryClosedPositionRepositoryAdapter(self.closed, self.tenant_id),
                FakePositionClosedNoticeAdapter(),
                self.exit_plans,
            )
        )
        self.recording = FakeLedgerRecordingAdapter(
            RecordAccountExecutionsUseCase(self.flows, self.activity, InMemoryPlatformOrdersAdapter(), self.ledger)
        )
        flow_state = ReadFlowStateUseCase(
            self.flows,
            self.activity,
            self.ledger,
            self.exit_plans,
            InMemoryFlowProtectionLevelsAdapter(ProtectionStore(), self.tenant_id),
        )
        self.notices = FakeCashOutNoticeAdapter()
        ports = CashOutPorts(flow_state, closings, self.recording, lambda: NOW, self.notices)
        self.cash_out = CashOutProfitsUseCase(self.flows, ports)

    def flow(self, *, status: FlowStatus = FlowStatus.ACTIVE, capital: str = "500") -> Flow:
        configuration = a_configuration(assets=("BTC",), allocated_capital=Decimal(capital))
        flow = a_flow(self.tenant_id, status=status, account_id=self.account_id, configuration=configuration)
        self.flows.add(flow)
        return flow

    def holding(self, flow: Flow, unrealized_pnl: str) -> None:
        reading = self.activity.activities[self.account_id]
        position = a_position("BTC", margin=Decimal(100), unrealized_pnl=Decimal(unrealized_pnl))
        self.activity.activities[self.account_id] = replace(reading, positions=(position,))
        self.ledger.expect(flow.id, "BTC", Decimal(1))

    def earned(self, flow: Flow, realized_pnl: str) -> None:
        fill = a_fill("SOL", uuid4(), realized_pnl=Decimal(realized_pnl), size=Decimal(0), fill_id="earned")
        self.ledger.add(self.account_id, flow.id, fill)


@pytest.fixture
def bench() -> Bench:
    return Bench()


def test_a_cash_out_closes_the_positions_and_frees_the_value_above_the_capital_kept(bench: Bench) -> None:
    flow = bench.flow()
    bench.holding(flow, "120")

    outcome = bench.cash_out.execute(CashOutProfitsCommand(flow.id, USER))

    assert (outcome.flow, outcome.freed, outcome.left_open) == (flow, Decimal(118), ())
    assert bench.exchange.closed == ["BTC"]
    assert bench.cycles.waited == [flow.id]
    assert bench.recording.recorded == [bench.account_id]
    assert tuple(bench.store.capital_changes.get(flow.id, [])) == (
        CapitalChange(
            flow.id,
            NOW,
            Decimal(500),
            Decimal(500),
            USER,
            CapitalChangeReason.CASH_OUT,
            Decimal(118),
            value_before=Decimal(618),
            cashed_profit=Decimal(118),
        ),
    )


def test_a_cash_out_keeping_the_capital_adds_no_version(bench: Bench) -> None:
    flow = bench.flow()
    bench.earned(flow, "118")

    bench.cash_out.execute(CashOutProfitsCommand(flow.id, USER))

    assert [version.number for version in bench.flows.versions(flow.id)] == [1]


def test_a_cash_out_to_a_capital_makes_it_the_next_version_and_frees_the_rest(bench: Bench) -> None:
    flow = bench.flow()
    bench.earned(flow, "118")

    outcome = bench.cash_out.execute(CashOutProfitsCommand(flow.id, USER, Decimal(400)))

    assert outcome.freed == Decimal(218)
    assert outcome.flow == bench.flows.get(flow.id) == flow.with_capital(Decimal(400))
    (change,) = tuple(bench.store.capital_changes.get(flow.id, []))
    assert (change.previous, change.new, change.amount, change.cashed_profit) == (
        Decimal(500),
        Decimal(400),
        Decimal(218),
        Decimal(118),
    )


@pytest.mark.parametrize("unrealized_pnl", ["-40", "0"])
def test_a_flow_without_profits_closes_nothing(bench: Bench, unrealized_pnl: str) -> None:
    flow = bench.flow()
    bench.holding(flow, unrealized_pnl)

    with pytest.raises(FlowWithoutProfitsError):
        bench.cash_out.execute(CashOutProfitsCommand(flow.id, USER))

    assert (bench.exchange.closed, bench.cycles.waited) == ([], [])


def test_a_capital_out_of_range_closes_nothing(bench: Bench) -> None:
    flow = bench.flow()
    bench.holding(flow, "120")

    with pytest.raises(CashOutCapitalOutOfRangeError):
        bench.cash_out.execute(CashOutProfitsCommand(flow.id, USER, Decimal(620)))

    assert bench.exchange.closed == []


def test_an_archived_flow_closes_nothing(bench: Bench) -> None:
    flow = bench.flow(status=FlowStatus.ARCHIVED)
    bench.earned(flow, "118")

    with pytest.raises(ArchivedFlowNotModifiableError):
        bench.cash_out.execute(CashOutProfitsCommand(flow.id, USER, Decimal(400)))

    assert bench.cycles.waited == []


def test_a_closing_refused_frees_nothing_and_comes_back_with_its_reason(bench: Bench) -> None:
    flow = bench.flow()
    bench.holding(flow, "120")
    bench.exchange.refusals["BTC"] = "Order rejected"

    outcome = bench.cash_out.execute(CashOutProfitsCommand(flow.id, USER))

    assert (outcome.flow, outcome.freed) == (flow, None)
    assert outcome.left_open == (PositionLeftOpen("BTC", "Order rejected"),)
    assert tuple(bench.store.capital_changes.get(flow.id, [])) == ()
    assert bench.recording.recorded == []
    assert bench.notices.told == []


def test_profits_gone_with_the_closings_free_nothing(bench: Bench) -> None:
    flow = bench.flow()
    bench.holding(flow, "1")
    bench.exchange.fee = Decimal(3)

    with pytest.raises(FlowWithoutProfitsError):
        bench.cash_out.execute(CashOutProfitsCommand(flow.id, USER))

    assert bench.exchange.closed == ["BTC"]
    assert tuple(bench.store.capital_changes.get(flow.id, [])) == ()
    assert bench.notices.told == []


def test_the_flow_keeps_its_status_and_every_closing_enters_the_history_as_a_cash_out(bench: Bench) -> None:
    flow = bench.flow(status=FlowStatus.PAUSED)
    bench.holding(flow, "120")

    outcome = bench.cash_out.execute(CashOutProfitsCommand(flow.id, USER))

    assert outcome.flow.status is bench.flows.get(flow.id).status is FlowStatus.PAUSED
    assert [(position.asset, position.reason) for position in bench.closed.positions] == [("BTC", CloseReason.CASH_OUT)]


def test_a_flow_of_another_tenant_is_not_found(bench: Bench) -> None:
    theirs = a_flow(TenantId.new(), status=FlowStatus.ACTIVE)
    bench.store.flows.append(theirs)

    with pytest.raises(FlowNotFoundError):
        bench.cash_out.execute(CashOutProfitsCommand(theirs.id, USER))


def test_a_cash_out_is_told_once_recorded_with_the_money_it_freed(bench: Bench) -> None:
    flow = bench.flow()
    bench.earned(flow, "118")

    bench.cash_out.execute(CashOutProfitsCommand(flow.id, USER))

    assert bench.notices.told == [(flow.name.value, Decimal(118))]
